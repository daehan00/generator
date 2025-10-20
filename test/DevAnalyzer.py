import logging
import os
import re
from typing import Dict, List, Set
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

from testAnalyzer import TestAnalyzer, BackendClient, Category, ResultDataFrames, ResultDataFrame
from Analyzer import BehaviorType

class DevAnalyzer(TestAnalyzer):
    def __init__(self, backend_client: BackendClient, time_filter_months: int = 7) -> None:
        super().__init__(backend_client)
        # DevAnalyzer 전용 로거 생성
        self.dev_logger = logging.getLogger("DevAnaly")
        # 필터링된 데이터 저장을 위한 디렉토리 설정
        self.output_dir = "filtered_data"
        # self._create_output_directory()
        
        # 브라우저 파일 화이트리스트 설정 (실제 파일명 형태)
        self.browser_whitelist: Set[str] = {
            "binary", "browser_collected_files", "browser_discovered_profiles",
            "Chrome.keyword_search_terms", "Edge.keyword_search_terms",
            "Chrome.keywords", "Edge.keywords",
            "Chrome.urls", "Edge.urls",
            "Chrome.visits", "Edge.visits", 
            "Chrome.visited_links", "Edge.visited_links",
            "Chrome.autofill", "Edge.autofill",
            # "Chrome.autofill_profiles", "Edge.autofill_profiles",
            "Chrome.addresses", "Edge.addresses",
            "Chrome.autofill_sync_metadata", "Edge.autofill_sync_metadata",
            # "Chrome.sync_entities_metadata", "Edge.sync_entities_metadata", 
            "Chrome.downloads", "Edge.downloads",
            "Chrome.downloads_url_chains", "Edge.downloads_url_chains",
            "Chrome.logins", "Edge.logins"
        }
        
        # 광고/추적 도메인 설정
        self.ad_tracking_domains: List[str] = [
            'doubleclick.net', 'googlesyndication.com', 'adnxs.com', 
            'google-analytics.com', 'scorecardresearch.com', 'facebook.net', 
            'akamaihd.net', 'cloudfront.net', 'gstatic.com'
        ]
        
        # 시간 필터링 기간 설정 (개월 수)
        self.time_filter_months: int = time_filter_months

        # 파일별 특정 시간 컬럼 필터링 규칙
        self.time_filter_config: Dict[str, str] = {
            "binary": "timestamp",
            "browser_collected_files": "timestamp",
            "Chrome.keywords": "last_visited",
            "Edge.keywords": "last_visited",
            "Chrome.urls": "last_visit_time",
            "Edge.urls": "last_visit_time",
            "Chrome.visits": "visit_time",
            "Edge.visits": "visit_time",
            "Chrome.autofill": "date_last_used",
            "Edge.autofill": "date_last_used",
            "Chrome.downloads": "end_time",
            "Edge.downloads": "end_time",
            "Chrome.logins": "date_last_used",
            "Edge.logins": "date_last_used",
            "Chrome.addresses": "use_date",
            "Edge.addresses": "use_date",
            "mft_deleted_files": "deletion_time",
            "recycle_bin_files": "deleted_time",
            "lnk_files": "target_info__target_times__access",
            "prefetch_files": "last_run_time_1",
            # "usb_devices": "setupapi_info__last_connection_time",
            "KakaoTalk.files": "last_modified",
            "Discord.files": "last_modified"
        }
    
    def _create_output_directory(self) -> None:
        """필터링된 데이터 저장을 위한 디렉토리 생성"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            #self.dev_logger.info(f"📁 [DEV] Created output directory: {self.output_dir}")
    
    def _save_filtered_data(self, category: Category, df_results: ResultDataFrames) -> str:
        """필터링된 데이터를 CSV 파일로 저장 (이미 필터링된 데이터라고 가정)"""
        if not df_results or not df_results.data:
            #self.dev_logger.info(f"⏭️ [DEV] No data to save for category: {category.name}")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_dir = os.path.join(self.output_dir, f"{category.name.lower()}_{timestamp}")
        
        # 저장할 데이터가 있으므로 바로 디렉토리 생성
        os.makedirs(category_dir)
        #self.dev_logger.info(f"📁 [DEV] Created category directory: {category_dir}")
        
        saved_count = 0
        for result in df_results.data:
            # 파일명에서 특수문자 제거 및 안전한 파일명 생성
            safe_filename = re.sub(r'[/\\:*?"<>|]', '_', result.name)
            if not safe_filename.endswith('.csv'):
                safe_filename += '.csv'
            
            file_path = os.path.join(category_dir, safe_filename)
            
            try:
                result.data.to_csv(file_path, index=False, encoding='utf-8-sig')
                #self.dev_logger.info(f"💾 [DEV] Saved filtered data: {file_path} ({len(result.data)} rows)")
                saved_count += 1
            except Exception as e:
                self.dev_logger.error(f"❌ [DEV] Failed to save {file_path}: {str(e)}")
        
        #self.dev_logger.info(f"✅ [DEV] Saved {saved_count} files to: {category_dir}")
        return category_dir
    
    def _filter_data(self, category: Category, df_results: ResultDataFrames) -> ResultDataFrames:
        """
        데이터 필터링 처리. 파일 선별을 먼저 수행한 후 데이터 필터링을 적용한다.
        순서: 파일 필터링 (화이트리스트, 빈 파일) → 데이터 필터링 (시간 → 열/행)
        """
        #self.dev_logger.info(f"🔧 [DEV] Starting _filter_data for category: {category.name}")
        
        if not df_results or not df_results.data:
            self.dev_logger.info(f"⏭️ [DEV] No data to filter for category: {category.name}")
            return ResultDataFrames(data=[])

        category_original_rows = 0
        category_filtered_rows = 0
        processed_data = []
        skipped_by_whitelist = 0

        for result in df_results.data:
            # --- 1. 파일 레벨 필터링 (처리 대상을 먼저 확정) ---
            if category == Category.BROWSER and result.name not in self.browser_whitelist:
                skipped_by_whitelist += 1
                continue
            
            if result.data.empty:
                continue
            
            original_count = len(result.data)
            category_original_rows += original_count

            # --- 2. 데이터 레벨 필터링 (확정된 파일에 대해서만 수행) ---
            # 2-1. 시간 필터링
            df = self._apply_time_filtering(result)
            
            # 2-2. 카테고리별 열/행 필터링 (임시 변수에 필터링 결과를 담음)
            temp_result = ResultDataFrame(name=result.name, data=df)
            match category:
                case Category.USB:
                    filtered_df = self._filter_usb_data(temp_result)
                case Category.LNK:
                    filtered_df = self._filter_lnk_data(temp_result)
                case Category.MESSENGER:
                    filtered_df = self._filter_messenger_data(temp_result)
                case Category.PREFETCH:
                    filtered_df = self._filter_prefetch_data(temp_result)
                case Category.DELETED:
                    filtered_df = self._filter_deleted_data(temp_result)
                case Category.BROWSER:
                    filtered_df = self._filter_browser_data(temp_result)
                case _:
                    self.dev_logger.warning(f"No specific filter for category {category.name}. Applying default limit.")
                    filtered_df = temp_result.data.head(10)
            
            final_count = len(filtered_df)

            # --- 3. 최종 결과 추가 ---
            # 모든 필터링 후 데이터가 남아있는 경우에만 최종 목록에 추가
            if final_count > 0:
                result.data = filtered_df
                category_filtered_rows += final_count
                processed_data.append(result)
                self.dev_logger.debug(f"🔧 [DEV] Filtered {result.name}: {original_count} -> {final_count} rows. Keeping file.")
            else:
                self.dev_logger.info(f"⏭️ [DEV] Dropping file {result.name} after filtering (0 rows remaining).")

        # if skipped_by_whitelist > 0:
        #     self.dev_logger.info(f"⏭️ [DEV] Skipped {skipped_by_whitelist} browser files (not in whitelist).")
            
        # 카테고리별 필터링 통계 로깅
        reduction = category_original_rows - category_filtered_rows
        reduction_percent = (reduction / category_original_rows * 100) if category_original_rows > 0 else 0
        self.dev_logger.info(f"📊 [DEV] {category.name} filtering summary: {category_original_rows:,} -> {category_filtered_rows:,} rows (reduction: {reduction:,} rows, {reduction_percent:.1f}%)")

        # 전체 통계 업데이트
        if not hasattr(self, '_total_original_rows'):
            self._total_original_rows = 0
            self._total_filtered_rows = 0
        self._total_original_rows += category_original_rows
        self._total_filtered_rows += category_filtered_rows

        # 최종적으로 필터링된 데이터로 새 객체 생성
        filtered_df_results = ResultDataFrames(data=processed_data)

        # 필터링된 데이터 저장
        # self._save_filtered_data(category, filtered_df_results)

        # self.dev_logger.info(f"✅ [DEV] Completed _filter_data for category: {category.name}")
        return filtered_df_results

    def _apply_time_filtering(self, result: ResultDataFrame) -> pd.DataFrame:
        """
        지정된 개월 수 이전부터 현재까지의 데이터만 유지하는 시간 필터링.
        파일별로 지정된 시간 컬럼이 있으면 해당 컬럼을 사용하고, 없으면 일반적인 시간 컬럼을 찾아 필터링.
        """
        df = result.data
        file_name = result.name

        if df.empty:
            return df

        current_time = datetime.now()
        cutoff_date = current_time - relativedelta(months=self.time_filter_months)
        
        # self.dev_logger.debug(
        #     f"⏰ [DEV] Time filtering for '{file_name}': Keeping data from "
        #     f"{cutoff_date.strftime('%Y-%m-%d')} to {current_time.strftime('%Y-%m-%d')}"
        # )

        target_columns = []
        
        # 1. 파일별 특정 시간 컬럼 규칙 확인
        specific_time_col = self.time_filter_config.get(file_name)
        if specific_time_col and specific_time_col in df.columns:
            # self.dev_logger.info(f"🎯 [DEV] Found specific time column for '{file_name}': '{specific_time_col}'")
            target_columns.append(specific_time_col)
        else:
            # 2. 특정 규칙이 없거나 컬럼이 없으면, 일반적인 시간 컬럼 탐색
            # if specific_time_col:
            #      self.dev_logger.warning(f"⚠️ [DEV] Specific time column '{specific_time_col}' not found in '{file_name}'. Falling back to general search.")
            
            time_keywords = ['time', 'date', 'created', 'modified', 'access', 'deletion', 'mtime', 'ctime', 'timestamp']
            target_columns = [
                col for col in df.columns 
                if isinstance(col, str) and any(keyword in col.lower() for keyword in time_keywords)
            ]

        if not target_columns:
            self.dev_logger.warning(f"ℹ️ [DEV] No time columns found for '{file_name}', skipping time filtering.")
            return df

        # 시간 필터링 적용 (OR 조건)
        mask = pd.Series([False] * len(df), index=df.index)
        
        for col in target_columns:
            try:
                # addresses 파일의 use_date 컬럼 특별 처리 (Unix timestamp)
                if 'addresses' in file_name and col == 'use_date':
                    # self.dev_logger.debug(f"🔍 [DEV] Converting Unix timestamp in {file_name}")
                    # Unix timestamp를 datetime으로 변환
                    temp_dates = self._smart_datetime_conversion(df[col], col)
                # cookies 파일의 WebKit timestamp 특별 처리
                elif 'cookies' in file_name and col.endswith('_utc'):
                    # self.dev_logger.debug(f"🔍 [DEV] Converting WebKit timestamp in {file_name}")
                    # WebKit timestamp (마이크로초)를 datetime으로 변환
                    temp_dates = self._smart_datetime_conversion(df[col], col)
                # 기타 WebKit timestamp 형식 처리 (큰 숫자 값들)
                elif col.endswith('_utc') and df[col].dtype in ['int64', 'float64']:
                    # 값이 매우 큰 경우 WebKit timestamp로 간주
                    sample_values = df[col].dropna().head(3)
                    if len(sample_values) > 0 and sample_values.iloc[0] > 1e15:  # WebKit timestamp 범위
                        # self.dev_logger.debug(f"🔍 [DEV] Converting WebKit timestamp for {col}")
                        temp_dates = self._smart_datetime_conversion(df[col], col)
                    else:
                        # 숫자형 데이터인 경우 Unix timestamp로 시도
                        temp_dates = self._smart_datetime_conversion(df[col], col)
                else:
                    # 일반적인 datetime 변환 - 먼저 데이터 타입과 샘플 값 확인
                    temp_dates = self._smart_datetime_conversion(df[col], col)
                
                # 타임존 정보가 있는 경우에만 tz_localize 적용
                if hasattr(temp_dates.dt, 'tz') and temp_dates.dt.tz is not None:
                    temp_dates = temp_dates.dt.tz_localize(None)
                
                # 유효한 날짜이고, cutoff_date 이후인 데이터만 선택
                valid_mask = temp_dates.notna() & (temp_dates >= cutoff_date)
                mask |= valid_mask
                
                if valid_mask.any():
                    self.dev_logger.debug(
                        f"⏰ [DEV] Column '{col}' contributed {valid_mask.sum()} valid rows for filtering."
                    )
            except Exception as e:
                self.dev_logger.warning(f"⚠️ [DEV] Could not filter by column '{col}' in '{file_name}': {str(e)}")
                continue
        
        # 필터링된 데이터프레임 반환
        return df[mask]

    def _smart_datetime_conversion(self, series: pd.Series, column_name: str) -> pd.Series:
        """
        스마트한 datetime 변환 - 데이터 타입과 샘플 값을 분석하여 최적의 변환 방법 선택
        """
        # Categorical 데이터 처리 (먼저 처리)
        if isinstance(series.dtype, pd.CategoricalDtype):
            # self.dev_logger.debug(f"🔍 [DEV] Converting categorical data to string for {column_name}")
            series = pd.Series(series.astype(str), index=series.index if hasattr(series, 'index') else None)
        
        if series.empty:
            return pd.Series([], dtype='datetime64[ns]')
        
        # 샘플 값들 확인 (NaN 제외)
        sample_values = series.dropna().head(5)
        if sample_values.empty:
            return pd.Series([pd.NaT] * len(series), index=series.index)
        
        # 숫자형 데이터인 경우 - 더 엄격한 체크
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_string_dtype(series):
            # Unix timestamp 범위 확인 (1970-2038년)
            min_val = sample_values.min()
            max_val = sample_values.max()
            
            if min_val > 1e15:  # WebKit timestamp (마이크로초)
                # self.dev_logger.debug(f"🔍 [DEV] Detected WebKit timestamp for {column_name}")
                return pd.to_datetime(series, unit='us', errors='coerce')
            elif min_val > 1e9:  # Unix timestamp (초)
                # self.dev_logger.debug(f"🔍 [DEV] Detected Unix timestamp for {column_name}")
                return pd.to_datetime(series, unit='s', errors='coerce')
            elif min_val > 1e6:  # 밀리초 timestamp
                # self.dev_logger.debug(f"🔍 [DEV] Detected millisecond timestamp for {column_name}")
                return pd.to_datetime(series, unit='ms', errors='coerce')
        
        # 문자열 데이터이거나 숫자형이지만 범위에 맞지 않는 경우
        sample_str = str(sample_values.iloc[0])
        
        # ISO 형식 확인
        if 'T' in sample_str and ('+' in sample_str or 'Z' in sample_str):
            # self.dev_logger.debug(f"🔍 [DEV] Detected ISO format for {column_name}")
            return pd.to_datetime(series, format='ISO8601', errors='coerce')
        
        # 일반적인 날짜 형식들 시도
        common_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S.%f%z'
        ]
        
        for fmt in common_formats:
            try:
                # 샘플 값으로 형식 테스트
                test_val = pd.to_datetime(sample_str, format=fmt, errors='coerce')
                if not pd.isna(test_val):
                    # self.dev_logger.debug(f"🔍 [DEV] Detected format '{fmt}' for {column_name}")
                    return pd.to_datetime(series, format=fmt, errors='coerce')
            except:
                continue
        
        # 모든 형식이 실패하면 기본 변환 (경고 억제)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            warnings.simplefilter("ignore", FutureWarning)
            # self.dev_logger.debug(f"🔍 [DEV] Using fallback datetime conversion for {column_name}")
            return pd.to_datetime(series, errors='coerce')

    def _filter_browser_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """브라우저 데이터에 대한 필터링 규칙"""
        # self.dev_logger.info(f"🔎 [DEV] Applying 'BROWSER' filter to {result.name}")
        df = result.data.copy()
        
        # 화이트리스트에 없는 파일은 건너뛰기
        if result.name not in self.browser_whitelist:
            # self.dev_logger.debug(f"⏭️ [DEV] Skipping browser file (not in whitelist): {result.name}")
            return pd.DataFrame()
        
        # 파일명에서 접두사 제거
        file_name = result.name.split('.', 1)[1] if result.name.startswith(('Chrome.', 'Edge.')) else result.name
        # self.dev_logger.debug(f"📁 [DEV] Processing browser file: {file_name}")
        
        # 1. 열 필터링
        columns_to_drop = self._get_browser_columns_to_drop(file_name)
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        
        if existing_columns_to_drop:
            df.drop(columns=existing_columns_to_drop, inplace=True)
            # self.dev_logger.debug(f"Dropped columns for {file_name}: {existing_columns_to_drop}")
        
        # 로그인 파일의 경우 첫 번째 컬럼(인덱스)도 제거
        if file_name == "logins" and len(df.columns) > 0:
            df.drop(columns=[df.columns[0]], inplace=True)
        
        # 2. 행 필터링
        df = self._apply_browser_row_filtering(df, file_name)
        
        # self.dev_logger.info(f"🌐 [DEV] Filtered {file_name}: {len(result.data)} -> {len(df)} rows")
        return df
    
    def _apply_browser_row_filtering(self, df: pd.DataFrame, file_name: str) -> pd.DataFrame:
        """브라우저 데이터에 대한 행 필터링 규칙 적용"""
        original_count = len(df)
        
        if file_name == "visits":
            if 'visit_duration' in df.columns:
                df['visit_duration'] = pd.to_numeric(df['visit_duration'], errors='coerce')
                df = df[df['visit_duration'] != 0]
                # self.dev_logger.info(f"🗑️ [DEV] Removed rows with visit_duration=0")
        
        elif file_name == "urls":
            if 'visit_count' in df.columns:
                df['visit_count'] = pd.to_numeric(df['visit_count'], errors='coerce')
                df = df[df['visit_count'] > 0]
            
            if 'url' in df.columns:
                pattern = '|'.join(self.ad_tracking_domains)
                df = df[~df['url'].str.contains(pattern, case=False, na=False)]
                # self.dev_logger.info(f"🗑️ [DEV] Removed ad/tracking domains")
        
        elif file_name == "downloads":
            # 완료된 다운로드만
            if 'state' in df.columns:
                df = df[df['state'].astype(str) == '1']
            
            # 임시 파일 제거
            if 'target_path' in df.columns:
                temp_pattern = r'\.(?:tmp|crdownload)$'  # non-capturing group 사용
                df = df[~df['target_path'].str.contains(temp_pattern, case=False, na=False)]
            
            # 빈 행 제거
            df = df.dropna(how='all')
            if 'target_path' in df.columns:
                df = df[df['target_path'].notna() & (df['target_path'].astype(str).str.strip() != '')]
            if 'url' in df.columns:
                df = df[df['url'].notna() & (df['url'].astype(str).str.strip() != '')]
        
        elif file_name == "browser_collected_files":
            if 'data_type' in df.columns and 'download_state' in df.columns:
                df = df[(df['data_type'] == 'downloads') & (df['download_state'] == 'completed')]
        
        elif file_name == "sync_entities_metadata":
            # 삭제된 항목 제거
            if 'is_deleted' in df.columns:
                df = df[df['is_deleted'] != True]
            
            # 폴더가 아닌 실제 데이터만 유지
            if 'is_folder' in df.columns:
                df = df[df['is_folder'] != True]
            
            # 빈 행 제거
            df = df.dropna(how='all')
        
        if original_count != len(df):
            self.dev_logger.info(f"🗑️ [DEV] Row filtering: {original_count} -> {len(df)} rows")
        
        return df
    
    def _get_browser_columns_to_drop(self, file_name: str) -> List[str]:
        """브라우저 파일명에 따른 제거할 컬럼 목록 반환"""
        column_map = {
            "binary": ['error', 'success', 'file_type'],
            "browser_collected_files": ['error', 'success', 'file_type'],
            "browser_discovered_profiles": ['exists'],
            "keyword_search_terms": ['normalized_term'],
            "keywords": [
                'url_hash', 'input_encodings', 'image_url_post_params', 
                'search_url_post_params', 'suggest_url_post_params',
                'alternate_urls', 'safe_for_autoreplace', 'created_from_play_api',
                'image_url', 'favicon_url'
            ],
            "urls": ['favicon_id'],
            "visits": ['incremented_omnibox_typed_score', 'app_id'],
            "autofill": ['value_lower'],
            "addresses": ['language_code'],
            "downloads": ['transient', 'http_method', 'etag', 'last_response_headers'],
            "logins": [
                'password_value', 'username_element', 'password_element', 
                'submit_element', 'display_name', 'icon_url', 'federation_url', 
                'skip_zero_click', 'generation_upload_status', 
                'possible_username_pairs', 'moving_blocked_for_list'
            ],
            "sync_entities_metadata": [
                'model_type', 'storage_key', 'client_tag_hash', 'server_id',
                'specifics_hash', 'base_specifics_hash', 'parent_id', 'version',
                'mtime', 'ctime', 'server_version', 'is_deleted', 'is_folder',
                'unique_position', 'is_bookmark', 'is_folder', 'is_unsynced'
            ]
        }
        return column_map.get(file_name, [])

    def _filter_deleted_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """삭제된 파일 데이터에 대한 필터링"""
        # self.dev_logger.info(f"🔎 [DEV] Applying 'DELETED' filter to {result.name}")
        df = result.data.copy()
        
        # 열 필터링
        columns_to_drop = [
            'access_time_timestamp', 'creation_time_timestamp', 
            'deletion_time_timestamp', 'modification_time_timestamp', 
            'deleted_time_timestamp', 'is_directory', 'parse_status', 
            'recycle_bin', 'recycle_bin_version', 'Unnamed: 0', 'file_index'
        ]
        
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        if existing_columns:
            df.drop(columns=existing_columns, inplace=True)
        
        # 행 필터링
        df = self._apply_deleted_row_filtering(df, result.name)
        return df
    
    def _apply_deleted_row_filtering(self, df: pd.DataFrame, file_name: str) -> pd.DataFrame:
        """삭제된 파일 데이터에 대한 행 필터링 (내부 유출 증거 보존 로직 강화)"""
        if 'mft_deleted' not in str(file_name).lower():
            return df
        
        original_count = len(df)
        
        # 시스템 파일 제거 ($ 접두사)
        file_col = 'file_name' if 'file_name' in df.columns else 'FileName'
        if file_col in df.columns:
            df = df[~df[file_col].str.startswith('$', na=False)]
        
        # 시스템 경로 제거 로직
        path_col = 'full_path' if 'full_path' in df.columns else 'ParentPath'
        if path_col in df.columns:
            # 1. 기본적으로 필터링할 시스템 경로 목록
            system_paths = [
                r'C:\\Windows', r'C:\\Program Files', 
                r'C:\\ProgramData', r'C:\\\$Recycle\.Bin'
            ]
            system_path_pattern = '|'.join(system_paths)
            # 시스템 경로에 해당하는 파일들을 식별 (True = 삭제 후보)
            is_in_system_path = df[path_col].str.contains(system_path_pattern, case=False, na=False, regex=True)

            # --- ✨ 새로운 예외 로직 시작 ✨ ---
            
            # 2. 필터링에서 제외할 예외 조건 정의
            # 2-1. 시스템 경로에 있더라도 보존해야 할 파일 확장자 목록
            suspicious_extensions = (
                '.zip', '.rar', '.7z', '.egg',  # 압축 파일
                '.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt', # 오피스 문서
                '.pdf', '.hwp' # 문서 파일
            )
            is_suspicious_extension = df[file_col].str.lower().str.endswith(suspicious_extensions, na=False)

            # 2-2. 공격자가 은닉을 위해 사용할 수 있는 특정 임시 폴더 목록
            allowed_temp_paths = [
                r'C:\\Windows\\Temp',  # Windows 공용 임시 폴더
                r'\\AppData\\Local\\Temp' # 사용자 프로필 임시 폴더 (경로에 포함되는지 검사)
            ]
            allowed_temp_pattern = '|'.join(allowed_temp_paths)
            is_in_allowed_temp_path = df[path_col].str.contains(allowed_temp_pattern, case=False, na=False, regex=True)

            # 3. 예외 조건 통합: 확장자가 의심스럽거나, 허용된 임시 폴더에 있으면 보존 (True = 보존)
            should_be_preserved = is_suspicious_extension | is_in_allowed_temp_path
            
            # --- ✨ 예외 로직 종료 ✨ ---

            # 4. 최종 필터링 적용: '삭제 후보'이면서 '보존' 대상이 아닌 파일만 실제 삭제
            rows_to_drop = is_in_system_path & ~should_be_preserved
            df = df[~rows_to_drop]

            # 시스템 로그 파일 제거 (이전과 동일)
            if file_col in df.columns:
                system_files = ['bootex.log', 'LOG', 'setup.log', 'install.log']
                system_pattern = '|'.join(system_files)
                df = df[~df[file_col].str.contains(system_pattern, case=False, na=False)]
        
        if original_count != len(df):
            self.dev_logger.info(f"🗑️ [DEV] Filtered: {original_count} -> {len(df)} rows")
        
        return df

    def _filter_lnk_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """LNK 데이터 필터링"""
        # self.dev_logger.info(f"🔎 [DEV] Applying 'LNK' filter to {result.name}")
        df = result.data.copy()
        
        # 열 필터링
        static_columns = [
            'header__header_size', 'header__header_size_hex', 
            'link_info__link_info_header_size', 'header__hot_key', 
            'header__icon_index', 'link_info__volume_info__drive_type',
            'link_info__volume_info__drive_type_formatted'
        ]
        
        pattern_columns = [
            col for col in df.columns 
            if isinstance(col, str) and (
                col.endswith(('_time_raw', '_hex', '_timestamp')) or 
                col.startswith('link_info__offsets__')
            )
        ]
        
        columns_to_drop = static_columns + pattern_columns
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        
        if existing_columns:
            df.drop(columns=existing_columns, inplace=True)
        
        # 행 필터링
        df = self._apply_lnk_row_filtering(df, result.name)
        return df
    
    def _apply_lnk_row_filtering(self, df: pd.DataFrame, file_name: str) -> pd.DataFrame:
        """LNK 행 필터링"""
        if 'lnk_files' not in str(file_name).lower():
            return df
        
        # 시스템 파일 제거
        target_col = next((col for col in ['Target_Path', 'target_info__target_path'] 
                          if col in df.columns), None)
        
        if target_col:
            system_keywords = [
                'Windows', 'System32', 'ProgramData', 'AppData', 
                'Update', 'Setup', 'Installer', 'MicrosoftEdge', 
                'Chrome', 'Temp', 'Cache'
            ]
            pattern = '|'.join(system_keywords)
            df = df[~df[target_col].str.contains(pattern, case=False, na=False)]
        
        return df

    def _filter_messenger_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """메신저 데이터 필터링"""
        # self.dev_logger.info(f"🔎 [DEV] Applying 'MESSENGER' filter to {result.name}")
        df = result.data.copy()
        
        # 열 필터링
        columns_to_drop = [
            'created_timestamp', 'last_modified_timestamp', 'relative_path',
            'is_valid_file', 'messenger_type', 'file_index'
        ]
        
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        if existing_columns:
            df.drop(columns=existing_columns, inplace=True)
        
        # 행 필터링
        df = self._apply_messenger_row_filtering(df, result.name)
        
        messenger_type = "Discord" if "Discord" in result.name else "KakaoTalk" if "KakaoTalk" in result.name else "Unknown"
        self.dev_logger.info(f"📱 [DEV] Processing {messenger_type}: {len(df)} rows")
        
        return df
    
    def _apply_messenger_row_filtering(self, df: pd.DataFrame, result_name: str) -> pd.DataFrame:
        """메신저 데이터 행 필터링"""
        if 'file_name' not in df.columns:
            # self.dev_logger.warning("⚠️ 'file_name' column not found, skipping extension filtering.")
            return df
        
        # 제외할 확장자
        exclude_extensions = (
            ".sys", ".ico", ".cur", ".msi", ".bat", ".sh",
            ".ttf", ".otf", ".editorconfig", ".eslintrc", ".npmignore"
        )
        
        initial_count = len(df)
        mask = ~df['file_name'].str.lower().str.endswith(exclude_extensions, na=False)
        filtered_df = df[mask]
        
        self.dev_logger.info(
            f"Filtered out {initial_count - len(filtered_df)} rows "
            f"based on {len(exclude_extensions)} excluded extensions."
        )
        
        return filtered_df

    def _filter_prefetch_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """Prefetch 데이터 필터링"""
        self.dev_logger.info(f"🔎 [DEV] Applying 'PREFETCH' filter to {result.name}")
        df = result.data.copy()
        
        columns_to_drop = [
            'structure__executable_file_name', 'file_index', 
            'structure__signature', 'structure__format_version', 
            'is_compressed', 'parse_success', 'error_message',
            'structure__trace_chains_offset', 'structure__volumes_info_offset',
            'structure__filename_strings_size', 'structure__filename_strings_offset'
        ]
        
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        if existing_columns:
            df.drop(columns=existing_columns, inplace=True)
        
        return df

    def _filter_usb_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """USB 데이터 필터링"""
        # self.dev_logger.info(f"🔎 [DEV] Applying 'USB' filter to {result.name}")
        df = result.data.copy()
        
        static_columns = [
            'volume_info__file_system', 'volume_info__mount_point', 
            'volume_info__volume_guid', 'volume_info__drive_letter', 
            'volume_info__volume_label', 'setupapi_info__serial_number', 
            'device_metadata__serial_number', 'setupapi_info__product_id', 
            'setupapi_info__volume_name', 'data_sources__has_usb_data', 
            'data_sources__has_usbstor_data', 'data_sources__has_setupapi_data', 
            'primary_source', 'portable_device_info__friendly_name'
        ]
        
        pattern_columns = [col for col in df.columns if col.startswith('connection_times__')]
        columns_to_drop = static_columns + pattern_columns
        
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        if existing_columns:
            df.drop(columns=existing_columns, inplace=True)
        
        return df

    
    
    def _load_data(self, category: Category) -> ResultDataFrames:
        """카테고리별 데이터 로드 - 파일이 없으면 건너뛰기"""
        try:
            # self.dev_logger.debug(f"Starting data load for category: {category.name}")
            
            # helper를 사용하여 데이터 로드 및 인코딩 처리
            df_results = self.helper.get_encoded_results(self.task_id, category)
            
            if not df_results:
                self.dev_logger.warning(f"No dataframes found for category {category.name} and task {self.task_id}")
                # 빈 ResultDataFrames 반환
                return ResultDataFrames(data=[])
            
            # self.dev_logger.debug(f"Successfully loaded {len(df_results.data)} dataframes for category: {category.name}")
            return df_results
            
        except Exception as e:
            # self.dev_logger.warning(f"⚠️ [DEV] Failed to load data for category {category.name}: {e}")
            # self.dev_logger.info(f"⏭️ [DEV] Skipping category {category.name} - no data available")
            # 빈 ResultDataFrames 반환하여 건너뛰기
            return ResultDataFrames(data=[])

    def _generate_analysis_result(self):
        """
        self.created_artifacts를 활용하여 행위별 분류결과를 생성함.
        결과는 상속받은 클래스에서 정의된 아래 self.analyze_results에 업데이트할 것.

        self.analyze_results = {
            behavior: {
                "job_id": self.job_id,
                "task_id": self.task_id,
                "behavior": behavior.name,
                "analysis_summary": "",
                "risk_level": "",
                "artifact_ids": []
            } for behavior in BehaviorType
        }
        행위별로 관련된 아티팩트만 분류하여 분석을 수행.
        """
        self.dev_logger.info("🔧 [DEV] Starting _generate_analysis_result (Behavior-specific Classification)")
        
        # 부모 클래스의 메서드 먼저 실행
        super()._generate_analysis_result()
        
        # created_artifacts가 비어있으면 조기 종료
        if not self.created_artifacts:
            self.dev_logger.warning("⚠️ [DEV] No artifacts created, skipping analysis result generation")
            return
        
        # 행위별 아티팩트 분류
        behavior_artifacts = self._classify_artifacts_by_behavior(self.created_artifacts)
        
        # 각 행위별로 분석 결과 생성
        for behavior_type in BehaviorType:
            if behavior_type in self.analyze_results:
                artifacts_for_behavior = behavior_artifacts.get(behavior_type, [])
                artifact_ids = [artifact.get('id') or artifact.get('artifact_id') 
                              for artifact in artifacts_for_behavior 
                              if artifact.get('id') or artifact.get('artifact_id')]
                
                # 행위별 분석 요약 생성
                analysis_summary = self._create_behavior_analysis_summary(behavior_type, artifacts_for_behavior)
                
                # 행위별 위험도 평가
                risk_level = self._evaluate_behavior_risk_level(behavior_type, artifacts_for_behavior)
                
                self.analyze_results[behavior_type].update({
                    "artifact_ids": artifact_ids,
                    "analysis_summary": analysis_summary,
                    "risk_level": risk_level,
                    "artifact_count": len(artifact_ids)
                })
                
                self.dev_logger.info(
                    f"✅ [DEV] {behavior_type.name}: {len(artifact_ids)} artifacts, risk={risk_level}"
                )
        
        # 전체 분석 통계 로깅
        self._log_behavior_analysis_statistics(behavior_artifacts)
        
        self.dev_logger.info("✅ [DEV] Completed _generate_analysis_result (Behavior-specific Classification)")


    def _classify_artifacts_by_behavior(self, artifacts: List[dict]) -> Dict[BehaviorType, List[dict]]:
        """아티팩트를 행위별로 분류"""
        behavior_artifacts = {behavior: [] for behavior in BehaviorType}
        
        for artifact in artifacts:
            artifact_type = artifact.get('artifact_type', '')
            
            # Acquisition (획득) - 다운로드, 브라우저, 메신저 관련
            if any(keyword in artifact_type.lower() for keyword in [
                'downloads', 'browser', 'messenger', 'discord', 'kakaotalk', 
                'urls', 'visits', 'autofill', 'logins'
            ]):
                behavior_artifacts[BehaviorType.acquisition].append(artifact)
            
            # Deletion (삭제) - 휴지통, 삭제된 파일 관련
            elif any(keyword in artifact_type.lower() for keyword in [
                'deleted', 'recycle', 'mft_deleted'
            ]):
                behavior_artifacts[BehaviorType.deletion].append(artifact)
            
            # Forgery (위조) - LNK 파일, Prefetch 관련
            elif any(keyword in artifact_type.lower() for keyword in [
                'lnk', 'prefetch'
            ]):
                behavior_artifacts[BehaviorType.forgery].append(artifact)
            
            # Upload (업로드) - USB 장치 관련
            elif any(keyword in artifact_type.lower() for keyword in [
                'usb'
            ]):
                behavior_artifacts[BehaviorType.upload].append(artifact)
            
            # Etc (기타) - 나머지 모든 것
            else:
                behavior_artifacts[BehaviorType.etc].append(artifact)
        
        return behavior_artifacts

    def _create_behavior_analysis_summary(self, behavior_type: BehaviorType, artifacts: List[dict]) -> str:
        """행위별 분석 요약 생성"""
        artifact_count = len(artifacts)
        
        if artifact_count == 0:
            return f"No artifacts found for {behavior_type.name} behavior."
        
        # 아티팩트 타입별 통계
        type_counts = {}
        for artifact in artifacts:
            artifact_type = artifact.get('artifact_type', 'unknown')
            type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
        
        # 상위 타입들
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        type_summary = ", ".join([f"{atype}: {count}" for atype, count in top_types])
        
        return (f"Analysis of {artifact_count} artifacts for {behavior_type.name} behavior. "
                f"Top artifact types: {type_summary}")

    def _evaluate_behavior_risk_level(self, behavior_type: BehaviorType, artifacts: List[dict]) -> str:
        """행위별 위험도 평가 - 모든 행위를 normal로 설정"""
        # 위험도 평가 없이 모든 행위를 normal로 설정
        return 'normal'

    def _log_behavior_analysis_statistics(self, behavior_artifacts: Dict[BehaviorType, List[dict]]):
        """행위별 분석 통계 로깅"""
        total_artifacts = sum(len(artifacts) for artifacts in behavior_artifacts.values())
        
        self.dev_logger.info("=" * 80)
        self.dev_logger.info("📊 [DEV] Behavior-specific Analysis Statistics")
        self.dev_logger.info("=" * 80)
        
        # 행위별 통계
        self.dev_logger.info("🔍 Behavior-wise Statistics:")
        for behavior_type, artifacts in behavior_artifacts.items():
            count = len(artifacts)
            percentage = (count / total_artifacts * 100) if total_artifacts > 0 else 0
            risk_level = self.analyze_results[behavior_type].get('risk_level', 'unknown')
            
            self.dev_logger.info(
                f"  • {behavior_type.name}: {count:,} artifacts ({percentage:.1f}%) - Risk: {risk_level}"
            )
        
        # 필터링 효과 통계
        total_original_rows = getattr(self, '_total_original_rows', 0)
        total_filtered_rows = getattr(self, '_total_filtered_rows', 0)
        filtering_reduction = total_original_rows - total_filtered_rows
        filtering_percentage = (filtering_reduction / total_original_rows * 100) if total_original_rows > 0 else 0
        
        if total_original_rows > 0:
            self.dev_logger.info("\n📉 Filtering Effectiveness:")
            self.dev_logger.info(f"  • Original Data: {total_original_rows:,} rows")
            self.dev_logger.info(f"  • Filtered Data: {total_filtered_rows:,} rows")
            self.dev_logger.info(f"  • Reduction: {filtering_reduction:,} rows ({filtering_percentage:.1f}%)")
        
        self.dev_logger.info("=" * 80)