import logging
import os
import re
from typing import Dict, List, Set
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

from test.testAnalyzer import TestAnalyzer, BackendClient, Category, ResultDataFrames, ResultDataFrame
from test.Analyzer import BehaviorType

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
            "Chrome.sync_entities_metadata", "Edge.sync_entities_metadata", 
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
            "usb_devices": "setupapi_info__last_connection_time",
            "KakaoTalk.files": "last_modified",
            "Discord.files": "last_modified"
        }
    
    def _create_output_directory(self) -> None:
        """필터링된 데이터 저장을 위한 디렉토리 생성"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.dev_logger.info(f"📁 [DEV] Created output directory: {self.output_dir}")
    
    def _save_filtered_data(self, category: Category, df_results: ResultDataFrames) -> str:
        """필터링된 데이터를 CSV 파일로 저장"""
        self._create_output_directory()
        # 빈 데이터인 경우 저장하지 않음
        if not df_results or not df_results.data:
            self.dev_logger.info(f"⏭️ [DEV] No data to save for category: {category.name}")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_dir = os.path.join(self.output_dir, f"{category.name.lower()}_{timestamp}")
        
        saved_count = 0
        skipped_count = 0
        empty_count = 0
        
        # 먼저 저장할 파일이 있는지 확인
        files_to_save = []
        for result in df_results.data:
            # 브라우저 카테고리의 경우 화이트리스트 확인
            if category == Category.BROWSER and result.name not in self.browser_whitelist:
                self.dev_logger.debug(f"⏭️ [DEV] Skipping browser file (not in whitelist): {result.name}")
                skipped_count += 1
                continue
            
            # 빈 데이터인 경우 건너뛰기
            if result.data.empty:
                self.dev_logger.info(f"⏭️ [DEV] Skipping empty file: {result.name} (0 rows)")
                empty_count += 1
                continue
            
            files_to_save.append(result)
        
        # 저장할 파일이 없으면 디렉토리 생성하지 않음
        if not files_to_save:
            self.dev_logger.info(f"⏭️ [DEV] No files to save for category: {category.name} (all files empty or skipped)")
            return ""
        
        # 디렉토리 생성
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
            self.dev_logger.info(f"📁 [DEV] Created category directory: {category_dir}")
        
        # 파일 저장
        for result in files_to_save:
            # 파일명에서 특수문자 제거 및 안전한 파일명 생성
            safe_filename = re.sub(r'[/\\:*?"<>|]', '_', result.name)
            if not safe_filename.endswith('.csv'):
                safe_filename += '.csv'
            
            file_path = os.path.join(category_dir, safe_filename)
            
            try:
                result.data.to_csv(file_path, index=False, encoding='utf-8-sig')
                self.dev_logger.info(f"💾 [DEV] Saved filtered data: {file_path} ({len(result.data)} rows)")
                saved_count += 1
            except Exception as e:
                self.dev_logger.error(f"❌ [DEV] Failed to save {file_path}: {str(e)}")
        
        self.dev_logger.info(f"✅ [DEV] Saved {saved_count} files, skipped {skipped_count} files, empty {empty_count} files to: {category_dir}")
        return category_dir
    
    def _filter_data(self, category: Category, df_results: ResultDataFrames) -> ResultDataFrames:
        """
        데이터 필터링 처리. 카테고리별로 받아서 데이터를 처리한다.
        """
        self.dev_logger.info(f"🔧 [DEV] Starting _filter_data for category: {category.name}")
        
        # 빈 데이터인 경우 조기 반환
        if not df_results or not df_results.data:
            self.dev_logger.info(f"⏭️ [DEV] No data to filter for category: {category.name}")
            return df_results
        
        # 필터링 통계 초기화
        category_original_rows = 0
        category_filtered_rows = 0
        
        for result in df_results.data:
            original_count = len(result.data)
            category_original_rows += original_count
            
            # 1. 시간 필터링
            result.data = self._apply_time_filtering(result)
            after_time_filter = len(result.data)
            if original_count != after_time_filter:
                self.dev_logger.info(f"⏰ [DEV] Time filtering for {result.name}: {original_count} -> {after_time_filter} rows")
            
            # 2. 카테고리별 열/행 필터링
            match category:
                case Category.USB:
                    result.data = self._filter_usb_data(result)
                case Category.LNK:
                    result.data = self._filter_lnk_data(result)
                case Category.MESSENGER:
                    result.data = self._filter_messenger_data(result)
                case Category.PREFETCH:
                    result.data = self._filter_prefetch_data(result)
                case Category.DELETED:
                    result.data = self._filter_deleted_data(result)
                case Category.BROWSER:
                    result.data = self._filter_browser_data(result)
                case _:
                    self.dev_logger.warning(f"No specific filter for category {category.name}. Applying default limit.")
                    result.data = result.data.head(10)
            
            final_count = len(result.data)
            category_filtered_rows += final_count
            
            self.dev_logger.debug(f"🔧 [DEV] Filtered {result.name} data: {original_count} -> {final_count} rows")
        
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
        
        # 필터링된 데이터를 CSV 파일로 저장
        # self._save_filtered_data(category, df_results)
        
        self.dev_logger.info(f"✅ [DEV] Completed _filter_data for category: {category.name}")
        return df_results

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
        
        self.dev_logger.debug(
            f"⏰ [DEV] Time filtering for '{file_name}': Keeping data from "
            f"{cutoff_date.strftime('%Y-%m-%d')} to {current_time.strftime('%Y-%m-%d')}"
        )

        target_columns = []
        
        # 1. 파일별 특정 시간 컬럼 규칙 확인
        specific_time_col = self.time_filter_config.get(file_name)
        if specific_time_col and specific_time_col in df.columns:
            self.dev_logger.info(f"🎯 [DEV] Found specific time column for '{file_name}': '{specific_time_col}'")
            target_columns.append(specific_time_col)
        else:
            # 2. 특정 규칙이 없거나 컬럼이 없으면, 일반적인 시간 컬럼 탐색
            if specific_time_col:
                 self.dev_logger.warning(f"⚠️ [DEV] Specific time column '{specific_time_col}' not found in '{file_name}'. Falling back to general search.")
            
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
                    self.dev_logger.debug(f"🔍 [DEV] Converting Unix timestamp in {file_name}")
                    # Unix timestamp를 datetime으로 변환
                    temp_dates = self._smart_datetime_conversion(df[col], col)
                # cookies 파일의 WebKit timestamp 특별 처리
                elif 'cookies' in file_name and col.endswith('_utc'):
                    self.dev_logger.debug(f"🔍 [DEV] Converting WebKit timestamp in {file_name}")
                    # WebKit timestamp (마이크로초)를 datetime으로 변환
                    temp_dates = self._smart_datetime_conversion(df[col], col)
                # 기타 WebKit timestamp 형식 처리 (큰 숫자 값들)
                elif col.endswith('_utc') and df[col].dtype in ['int64', 'float64']:
                    # 값이 매우 큰 경우 WebKit timestamp로 간주
                    sample_values = df[col].dropna().head(3)
                    if len(sample_values) > 0 and sample_values.iloc[0] > 1e15:  # WebKit timestamp 범위
                        self.dev_logger.debug(f"🔍 [DEV] Converting WebKit timestamp for {col}")
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
            self.dev_logger.debug(f"🔍 [DEV] Converting categorical data to string for {column_name}")
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
                self.dev_logger.debug(f"🔍 [DEV] Detected WebKit timestamp for {column_name}")
                return pd.to_datetime(series, unit='us', errors='coerce')
            elif min_val > 1e9:  # Unix timestamp (초)
                self.dev_logger.debug(f"🔍 [DEV] Detected Unix timestamp for {column_name}")
                return pd.to_datetime(series, unit='s', errors='coerce')
            elif min_val > 1e6:  # 밀리초 timestamp
                self.dev_logger.debug(f"🔍 [DEV] Detected millisecond timestamp for {column_name}")
                return pd.to_datetime(series, unit='ms', errors='coerce')
        
        # 문자열 데이터이거나 숫자형이지만 범위에 맞지 않는 경우
        sample_str = str(sample_values.iloc[0])
        
        # ISO 형식 확인
        if 'T' in sample_str and ('+' in sample_str or 'Z' in sample_str):
            self.dev_logger.debug(f"🔍 [DEV] Detected ISO format for {column_name}")
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
                    self.dev_logger.debug(f"🔍 [DEV] Detected format '{fmt}' for {column_name}")
                    return pd.to_datetime(series, format=fmt, errors='coerce')
            except:
                continue
        
        # 모든 형식이 실패하면 기본 변환 (경고 억제)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            warnings.simplefilter("ignore", FutureWarning)
            self.dev_logger.debug(f"🔍 [DEV] Using fallback datetime conversion for {column_name}")
            return pd.to_datetime(series, errors='coerce')

    def _filter_browser_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """브라우저 데이터에 대한 필터링 규칙"""
        self.dev_logger.info(f"🔎 [DEV] Applying 'BROWSER' filter to {result.name}")
        df = result.data.copy()
        
        # 화이트리스트에 없는 파일은 건너뛰기
        if result.name not in self.browser_whitelist:
            self.dev_logger.debug(f"⏭️ [DEV] Skipping browser file (not in whitelist): {result.name}")
            return pd.DataFrame()
        
        # 파일명에서 접두사 제거
        file_name = result.name.split('.', 1)[1] if result.name.startswith(('Chrome.', 'Edge.')) else result.name
        self.dev_logger.debug(f"📁 [DEV] Processing browser file: {file_name}")
        
        # 1. 열 필터링
        columns_to_drop = self._get_browser_columns_to_drop(file_name)
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        
        if existing_columns_to_drop:
            df.drop(columns=existing_columns_to_drop, inplace=True)
            self.dev_logger.debug(f"Dropped columns for {file_name}: {existing_columns_to_drop}")
        
        # 로그인 파일의 경우 첫 번째 컬럼(인덱스)도 제거
        if file_name == "logins" and len(df.columns) > 0:
            df.drop(columns=[df.columns[0]], inplace=True)
        
        # 2. 행 필터링
        df = self._apply_browser_row_filtering(df, file_name)
        
        self.dev_logger.info(f"🌐 [DEV] Filtered {file_name}: {len(result.data)} -> {len(df)} rows")
        return df
    
    def _apply_browser_row_filtering(self, df: pd.DataFrame, file_name: str) -> pd.DataFrame:
        """브라우저 데이터에 대한 행 필터링 규칙 적용"""
        original_count = len(df)
        
        if file_name == "visits":
            if 'visit_duration' in df.columns:
                df['visit_duration'] = pd.to_numeric(df['visit_duration'], errors='coerce')
                df = df[df['visit_duration'] != 0]
                self.dev_logger.info(f"🗑️ [DEV] Removed rows with visit_duration=0")
        
        elif file_name == "urls":
            if 'visit_count' in df.columns:
                df['visit_count'] = pd.to_numeric(df['visit_count'], errors='coerce')
                df = df[df['visit_count'] > 0]
            
            if 'url' in df.columns:
                pattern = '|'.join(self.ad_tracking_domains)
                df = df[~df['url'].str.contains(pattern, case=False, na=False)]
                self.dev_logger.info(f"🗑️ [DEV] Removed ad/tracking domains")
        
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
        self.dev_logger.info(f"🔎 [DEV] Applying 'DELETED' filter to {result.name}")
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
        """삭제된 파일 데이터에 대한 행 필터링"""
        if 'mft_deleted' not in str(file_name).lower():
            return df
        
        original_count = len(df)
        
        # 시스템 파일 제거 ($ 접두사)
        file_col = 'file_name' if 'file_name' in df.columns else 'FileName'
        if file_col in df.columns:
            df = df[~df[file_col].str.startswith('$', na=False)]
        
        # 시스템 경로 제거
        path_col = 'full_path' if 'full_path' in df.columns else 'ParentPath'
        if path_col in df.columns:
            system_paths = [
                r'C:\\Windows', r'C:\\Program Files', 
                r'C:\\ProgramData', r'C:\\\$Recycle\.Bin'
            ]
            pattern = '|'.join(system_paths)
            df = df[~df[path_col].str.contains(pattern, case=False, na=False, regex=True)]
            
            # 시스템 로그 파일 제거
            if file_col in df.columns:
                system_files = ['bootex.log', 'LOG', 'setup.log', 'install.log']
                system_pattern = '|'.join(system_files)
                df = df[~df[file_col].str.contains(system_pattern, case=False, na=False)]
        
        if original_count != len(df):
            self.dev_logger.info(f"🗑️ [DEV] Filtered: {original_count} -> {len(df)} rows")
        
        return df

    def _filter_lnk_data(self, result: ResultDataFrame) -> pd.DataFrame:
        """LNK 데이터 필터링"""
        self.dev_logger.info(f"🔎 [DEV] Applying 'LNK' filter to {result.name}")
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
        self.dev_logger.info(f"🔎 [DEV] Applying 'MESSENGER' filter to {result.name}")
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
            self.dev_logger.warning("⚠️ 'file_name' column not found, skipping extension filtering.")
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
        self.dev_logger.info(f"🔎 [DEV] Applying 'USB' filter to {result.name}")
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
            self.dev_logger.debug(f"Starting data load for category: {category.name}")
            
            # helper를 사용하여 데이터 로드 및 인코딩 처리
            df_results = self.helper.get_encoded_results(self.task_id, category)
            
            if not df_results:
                self.dev_logger.warning(f"No dataframes found for category {category.name} and task {self.task_id}")
                # 빈 ResultDataFrames 반환
                return ResultDataFrames(data=[])
            
            self.dev_logger.debug(f"Successfully loaded {len(df_results.data)} dataframes for category: {category.name}")
            return df_results
            
        except Exception as e:
            self.dev_logger.warning(f"⚠️ [DEV] Failed to load data for category {category.name}: {e}")
            self.dev_logger.info(f"⏭️ [DEV] Skipping category {category.name} - no data available")
            # 빈 ResultDataFrames 반환하여 건너뛰기
            return ResultDataFrames(data=[])

    # def _generate_analysis_result(self):
    #     """
    #     self.created_artifacts를 활용하여 분류결과를 생성함.
    #     결과는 상속받은 클래스에서 정의된 아래 self.analyze_results에 업데이트할 것.

    #     self.analyze_results = {
    #         behavior: {
    #             "job_id": self.job_id,
    #             "task_id": self.task_id,
    #             "behavior": behavior.name,
    #             "analysis_summary": "",
    #             "risk_level": "",
    #             "artifact_ids": []
    #         } for behavior in BehaviorType
    #     }
    #     """
    #     self.dev_logger.info("🔧 [DEV] Starting _generate_analysis_result")
        
    #     # 부모 클래스의 메서드 먼저 실행
    #     super()._generate_analysis_result()
        
    #     # created_artifacts가 비어있으면 조기 종료
    #     if not self.created_artifacts:
    #         self.dev_logger.warning("⚠️ [DEV] No artifacts created, skipping analysis result generation")
    #         return
        
    #     # 각 행위 유형별로 아티팩트 분석
    #     for behavior_type in BehaviorType:
    #         self.dev_logger.debug(f"🔍 [DEV] Analyzing behavior type: {behavior_type.name}")
            
    #         # 해당 행위와 관련된 아티팩트 수집
    #         related_artifacts = self._get_artifacts_by_behavior(behavior_type)
            
    #         if not related_artifacts:
    #             self.dev_logger.debug(f"ℹ️ [DEV] No artifacts found for {behavior_type.name}")
    #             continue
            
    #         # 아티팩트 ID 목록 추출
    #         artifact_ids = [artifact.get('id') or artifact.get('artifact_id') 
    #                     for artifact in related_artifacts 
    #                     if artifact.get('id') or artifact.get('artifact_id')]
            
    #         # 분석 요약 생성
    #         analysis_summary = self._create_analysis_summary(behavior_type, related_artifacts)
            
    #         # 위험도 평가
    #         risk_level = self._evaluate_risk_level(behavior_type, related_artifacts)
            
    #         # 결과 업데이트
    #         if behavior_type in self.analyze_results:
    #             self.analyze_results[behavior_type].update({
    #                 "artifact_ids": artifact_ids,
    #                 "analysis_summary": analysis_summary,
    #                 "risk_level": risk_level,
    #                 "artifact_count": len(artifact_ids)
    #             })
                
    #             self.dev_logger.info(
    #                 f"✅ [DEV] Updated {behavior_type.name}: "
    #                 f"{len(artifact_ids)} artifacts, risk={risk_level}"
    #             )
        
    #     # 전체 분석 통계 로깅
    #     self._log_analysis_statistics()
        
    #     self.dev_logger.info("✅ [DEV] Completed _generate_analysis_result")


    # def _get_artifacts_by_behavior(self, behavior_type: BehaviorType) -> List[dict]:
    #     """특정 행위 유형과 관련된 아티팩트 필터링"""
    #     related_artifacts = []
        
    #     for artifact in self.created_artifacts:
    #         # 아티팩트의 카테고리나 메타데이터를 기반으로 행위 유형 매칭
    #         artifact_behavior = artifact.get('behavior_type') or artifact.get('category')
            
    #         # 직접 매칭
    #         if artifact_behavior == behavior_type:
    #             related_artifacts.append(artifact)
    #             continue
            
    #         # 카테고리 기반 매핑
    #         if self._is_artifact_related_to_behavior(artifact, behavior_type):
    #             related_artifacts.append(artifact)
        
    #     return related_artifacts


    # def _is_artifact_related_to_behavior(self, artifact: dict, behavior_type: BehaviorType) -> bool:
    #     """아티팩트가 특정 행위 유형과 관련이 있는지 판단"""
    #     category = artifact.get('category', '').lower()
    #     artifact_type = artifact.get('type', '').lower()
    #     file_name = artifact.get('file_name', '').lower()
        
    #     # 행위 유형별 매핑 규칙
    #     behavior_mappings = {
    #         BehaviorType.USB_USAGE: ['usb', 'external_device', 'removable'],
    #         BehaviorType.FILE_ACCESS: ['lnk', 'shortcut', 'recent', 'jump_list'],
    #         BehaviorType.WEB_BROWSING: ['browser', 'chrome', 'edge', 'firefox', 'url', 'download'],
    #         BehaviorType.MESSENGER_USAGE: ['messenger', 'kakao', 'discord', 'telegram', 'chat'],
    #         BehaviorType.PROGRAM_EXECUTION: ['prefetch', 'execution', 'process', 'application'],
    #         BehaviorType.FILE_DELETION: ['deleted', 'recycle', 'mft_deleted', 'removed'],
    #         BehaviorType.DATA_EXFILTRATION: ['download', 'transfer', 'upload', 'export'],
    #     }
        
    #     # 해당 행위 유형의 키워드 확인
    #     keywords = behavior_mappings.get(behavior_type, [])
        
    #     return any(keyword in category or keyword in artifact_type or keyword in file_name 
    #             for keyword in keywords)


    # def _create_analysis_summary(self, behavior_type: BehaviorType, artifacts: List[dict]) -> str:
    #     """행위 유형별 분석 요약 생성"""
    #     artifact_count = len(artifacts)
        
    #     # 행위 유형별 요약 템플릿
    #     summary_templates = {
    #         BehaviorType.USB_USAGE: self._summarize_usb_usage,
    #         BehaviorType.FILE_ACCESS: self._summarize_file_access,
    #         BehaviorType.WEB_BROWSING: self._summarize_web_browsing,
    #         BehaviorType.MESSENGER_USAGE: self._summarize_messenger_usage,
    #         BehaviorType.PROGRAM_EXECUTION: self._summarize_program_execution,
    #         BehaviorType.FILE_DELETION: self._summarize_file_deletion,
    #         BehaviorType.DATA_EXFILTRATION: self._summarize_data_exfiltration,
    #     }
        
    #     # 해당 행위에 맞는 요약 함수 실행
    #     summarize_func = summary_templates.get(behavior_type)
    #     if summarize_func:
    #         return summarize_func(artifacts)
        
    #     # 기본 요약
    #     return f"Found {artifact_count} artifact(s) related to {behavior_type.name}"


    # def _summarize_usb_usage(self, artifacts: List[dict]) -> str:
    #     """USB 사용 분석 요약"""
    #     device_count = len(set(a.get('device_id') for a in artifacts if a.get('device_id')))
    #     connection_count = sum(a.get('connection_count', 1) for a in artifacts)
        
    #     return (f"Detected {device_count} unique USB device(s) with "
    #             f"{connection_count} total connection(s). "
    #             f"Analysis based on {len(artifacts)} artifact(s).")


    # def _summarize_file_access(self, artifacts: List[dict]) -> str:
    #     """파일 접근 분석 요약"""
    #     file_types = set()
    #     for artifact in artifacts:
    #         file_name = artifact.get('file_name', '')
    #         if '.' in file_name:
    #             ext = file_name.rsplit('.', 1)[-1].lower()
    #             file_types.add(ext)
        
    #     accessed_files = len(artifacts)
    #     return (f"Analyzed {accessed_files} file access record(s) "
    #             f"across {len(file_types)} file type(s): {', '.join(sorted(file_types)[:5])}")


    # def _summarize_web_browsing(self, artifacts: List[dict]) -> str:
    #     """웹 브라우징 분석 요약"""
    #     url_count = sum(1 for a in artifacts if 'url' in str(a.get('type', '')).lower())
    #     download_count = sum(1 for a in artifacts if 'download' in str(a.get('type', '')).lower())
        
    #     return (f"Analyzed {len(artifacts)} web browsing artifact(s): "
    #             f"{url_count} URL visit(s), {download_count} download(s)")


    # def _summarize_messenger_usage(self, artifacts: List[dict]) -> str:
    #     """메신저 사용 분석 요약"""
    #     messenger_types = set(a.get('messenger_type') for a in artifacts if a.get('messenger_type'))
    #     file_count = len(artifacts)
        
    #     if messenger_types:
    #         messengers = ', '.join(sorted(messenger_types))
    #         return f"Detected {file_count} messenger file(s) from: {messengers}"
        
    #     return f"Detected {file_count} messenger-related file(s)"


    # def _summarize_program_execution(self, artifacts: List[dict]) -> str:
    #     """프로그램 실행 분석 요약"""
    #     programs = set(a.get('program_name') or a.get('executable_name') 
    #                 for a in artifacts 
    #                 if a.get('program_name') or a.get('executable_name'))
        
    #     return (f"Identified {len(programs)} unique program(s) executed. "
    #             f"Total {len(artifacts)} execution record(s).")


    # def _summarize_file_deletion(self, artifacts: List[dict]) -> str:
    #     """파일 삭제 분석 요약"""
    #     deleted_count = len(artifacts)
    #     total_size = sum(a.get('file_size', 0) for a in artifacts)
        
    #     size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
    #     return (f"Found {deleted_count} deleted file(s). "
    #             f"Total size: {size_mb:.2f} MB")


    # def _summarize_data_exfiltration(self, artifacts: List[dict]) -> str:
    #     """데이터 유출 분석 요약"""
    #     transfer_count = len(artifacts)
    #     suspicious_count = sum(1 for a in artifacts if a.get('is_suspicious', False))
        
    #     return (f"Detected {transfer_count} data transfer event(s). "
    #             f"{suspicious_count} flagged as potentially suspicious.")


    # def _evaluate_risk_level(self, behavior_type: BehaviorType, artifacts: List[dict]) -> str:
    #     """위험도 평가"""
    #     artifact_count = len(artifacts)
        
    #     # 행위 유형별 기본 위험도
    #     base_risk = {
    #         BehaviorType.DATA_EXFILTRATION: 'HIGH',
    #         BehaviorType.FILE_DELETION: 'MEDIUM',
    #         BehaviorType.USB_USAGE: 'MEDIUM',
    #         BehaviorType.WEB_BROWSING: 'LOW',
    #         BehaviorType.MESSENGER_USAGE: 'LOW',
    #         BehaviorType.FILE_ACCESS: 'LOW',
    #         BehaviorType.PROGRAM_EXECUTION: 'LOW',
    #     }
        
    #     risk = base_risk.get(behavior_type, 'LOW')
        
    #     # 아티팩트 수에 따른 위험도 조정
    #     if artifact_count > 100:
    #         if risk == 'LOW':
    #             risk = 'MEDIUM'
    #         elif risk == 'MEDIUM':
    #             risk = 'HIGH'
    #     elif artifact_count > 50:
    #         if risk == 'LOW':
    #             risk = 'MEDIUM'
        
    #     # 의심스러운 패턴 감지
    #     suspicious_count = sum(1 for a in artifacts if a.get('is_suspicious', False))
    #     if suspicious_count > artifact_count * 0.3:  # 30% 이상이 의심스러운 경우
    #         if risk == 'LOW':
    #             risk = 'MEDIUM'
    #         elif risk == 'MEDIUM':
    #             risk = 'HIGH'
        
    #     return risk


    # def _log_analysis_statistics(self):
    #     """전체 분석 통계 로깅 - 업그레이드된 버전"""
    #     total_artifacts = len(self.created_artifacts)
    #     behaviors_with_data = sum(1 for result in self.analyze_results.values() 
    #                             if result.get('artifact_count', 0) > 0)
        
    #     high_risk_count = sum(1 for result in self.analyze_results.values() 
    #                         if result.get('risk_level') == 'HIGH')
    #     medium_risk_count = sum(1 for result in self.analyze_results.values() 
    #                         if result.get('risk_level') == 'MEDIUM')
    #     low_risk_count = sum(1 for result in self.analyze_results.values() 
    #                         if result.get('risk_level') == 'LOW')
        
    #     # 카테고리별 통계 계산
    #     category_stats = {}
    #     for artifact in self.created_artifacts:
    #         category = artifact.get('category', 'Unknown')
    #         if category not in category_stats:
    #             category_stats[category] = {'count': 0, 'risk_levels': []}
    #         category_stats[category]['count'] += 1
    #         category_stats[category]['risk_levels'].append(artifact.get('risk_level', 'UNKNOWN'))
        
    #     # 필터링 효과 통계 (원본 데이터와 비교)
    #     total_original_rows = getattr(self, '_total_original_rows', 0)
    #     total_filtered_rows = getattr(self, '_total_filtered_rows', 0)
    #     filtering_reduction = total_original_rows - total_filtered_rows
    #     filtering_percentage = (filtering_reduction / total_original_rows * 100) if total_original_rows > 0 else 0
        
    #     # 상세 통계 로깅
    #     self.dev_logger.info("=" * 80)
    #     self.dev_logger.info("📊 [DEV] Enhanced Analysis Statistics Summary")
    #     self.dev_logger.info("=" * 80)
        
    #     # 기본 통계
    #     self.dev_logger.info("🔍 Basic Statistics:")
    #     self.dev_logger.info(f"  • Total Artifacts: {total_artifacts:,}")
    #     self.dev_logger.info(f"  • Behaviors with Data: {behaviors_with_data}/{len(BehaviorType)}")
    #     self.dev_logger.info(f"  • Data Coverage: {(behaviors_with_data/len(BehaviorType)*100):.1f}%")
        
    #     # 위험도 분포
    #     self.dev_logger.info("\n⚠️ Risk Level Distribution:")
    #     self.dev_logger.info(f"  • High Risk: {high_risk_count} behaviors")
    #     self.dev_logger.info(f"  • Medium Risk: {medium_risk_count} behaviors")
    #     self.dev_logger.info(f"  • Low Risk: {low_risk_count} behaviors")
        
    #     # 필터링 효과
    #     if total_original_rows > 0:
    #         self.dev_logger.info("\n📉 Filtering Effectiveness:")
    #         self.dev_logger.info(f"  • Original Data: {total_original_rows:,} rows")
    #         self.dev_logger.info(f"  • Filtered Data: {total_filtered_rows:,} rows")
    #         self.dev_logger.info(f"  • Reduction: {filtering_reduction:,} rows ({filtering_percentage:.1f}%)")
        
    #     # 카테고리별 통계
    #     if category_stats:
    #         self.dev_logger.info("\n📁 Category-wise Statistics:")
    #         for category, stats in sorted(category_stats.items()):
    #             risk_distribution = {}
    #             for risk in stats['risk_levels']:
    #                 risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
                
    #             risk_str = ", ".join([f"{risk}: {count}" for risk, count in risk_distribution.items()])
    #             self.dev_logger.info(f"  • {category}: {stats['count']} artifacts ({risk_str})")
        
    #     # 행위별 상세 통계
    #     self.dev_logger.info("\n🎯 Behavior-wise Details:")
    #     for behavior_type, result in self.analyze_results.items():
    #         artifact_count = result.get('artifact_count', 0)
    #         if artifact_count > 0:
    #             risk_level = result.get('risk_level', 'UNKNOWN')
    #             analysis_summary = result.get('analysis_summary', 'No summary available')
                
    #             # 위험도에 따른 이모지
    #             risk_emoji = {
    #                 'HIGH': '🔴',
    #                 'MEDIUM': '🟡', 
    #                 'LOW': '🟢',
    #                 'UNKNOWN': '⚪'
    #             }.get(risk_level, '⚪')
                
    #             self.dev_logger.info(f"  {risk_emoji} {behavior_type.name}:")
    #             self.dev_logger.info(f"    • Artifacts: {artifact_count}")
    #             self.dev_logger.info(f"    • Risk Level: {risk_level}")
    #             self.dev_logger.info(f"    • Summary: {analysis_summary[:100]}{'...' if len(analysis_summary) > 100 else ''}")
        
    #     # 성능 통계
    #     processing_time = getattr(self, '_processing_time', 0)
    #     if processing_time > 0:
    #         self.dev_logger.info(f"\n⏱️ Performance:")
    #         self.dev_logger.info(f"  • Processing Time: {processing_time:.2f} seconds")
    #         if total_artifacts > 0:
    #             self.dev_logger.info(f"  • Artifacts per Second: {total_artifacts/processing_time:.2f}")
        
    #     self.dev_logger.info("=" * 80)

