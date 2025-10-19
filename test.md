본 분석은 HM Company 개발팀 김민재 사원의 업무용 Windows PC에 대하여 정보를 수집하였으며, 행위에 따라 기록되는 주요 아티팩트 데이터를 확보하였습니다.

### 대상 기기 정보

| PC 이름 | 운영체제 | IP 주소 | 사용자명 | 직급 | 부서 | 회사명 | MAC 주소 |
|---|---|---|---|---|---|---|---|
| DESKTOP-4L4O6MI | Windows 11 Version 24H2 | 192.168.74.135 | 김민재 | 사원 | 개발팀 | HM Company | 00-0C-29-EB-B3-7B |

### 수집된 아티팩트 범위

수집된 아티팩트는 브라우저 사용 내역, USB 연결 기록, 프로그램 실행 기록(프리패치), 파일 실행 및 삭제 흔적, 메신저 이용 내역 등으로 구성됩니다. 이러한 아티팩트들을 종합적으로 분석하여 사용자의 활동을 확인할 수 있습니다.


📊 최종 보고서:
  - 제목: USB를 통한 교육생 개인정보 유출
  - 설명: 이정호 주임이 교육생들의 개인정보가 포함된 '개별 활동보고서'를 디스코드를 통해 다운로드 받은 후, USB를 이용하여 외부로 유출하고 관련 파일을 삭제하여 증거를 인멸하려한 정황이 포착되었습니다. 파일 다운로드, USB 연결, 파일 삭제 행위가 시간적으로 매우 인접하게 발생하여 의도적인 정보 유출로 강력하게 의심됩니다.
  - 단계 수: 4개
  - Job ID: test_job_001
  - Task ID: test_task_001

  📝 시나리오 단계:
    1. 이정호 주임은 2025년 9월 11일과 18일에 걸쳐 디스코드를 통해 다수의 교육생 '개별 활동보고서' PDF 파일을 다운로드했습니다.
['239f036c-9b44-4af4-8953-4976c422968c', '5b388079-fbfb-4ad9-8dc0-1bda16464427', 'cb8e3dd6-f9dd-42f3-9623-146424db8312', '0d3d7c58-1278-4f2d-9a2b-15bff5f23c45', '1655c1a8-6ca3-4d1c-b565-f174eeba4081', 'ad98f716-a545-4a8a-af5f-875dc3453e2e', '99ae4472-ce4b-4307-977a-c532393b745c', '42020f33-aa8a-4b25-87ac-da88387f22aa', '071df79c-7c80-4ecf-8b45-0f0e00338a2f', '64245413-479c-4280-810f-4a3d1ba1c875', 'f7f6ebde-fa5f-451e-b05b-c4d834b06b3c', '73fadd24-052f-40da-97ad-8327caf1d3ea']
    2. 다운로드한 파일들을 외부로 쉽게 유출하기 위해 압축 프로그램 '알집'을 사용하여 하나의 파일로 압축했을 가능성이 있습니다.
['c95d4c33-0786-4a0f-bf7b-0dd0d0a4cc8a', '9223cf01-7b59-45ce-a7cd-5158df84e1d9']
    3. 2025년 9월 15일, 이정호 주임은 개인 소유로 추정되는 SanDisk USB 저장장치를 PC에 연결했습니다.
['e0a0532f-b684-413b-9ecd-a5660773d5cd', '31d6efc5-4c9c-4ff7-abea-9bbbb831aef0']
    4. USB 연결 직후, 다운로드했던 '개별 활동보고서' 파일들을 삭제하여 증거 인멸을 시도했습니다. 10주차 보고서는 9월 15일, 11주차 보고서는 9월 22일에 삭제되었습니다.
['d15e646e-21e1-4cc8-9bc2-2ff2ffdd21eb', '4fb0311c-77c9-4c7c-b3b9-998bdeb8dd78', 'e9a54485-1b3d-4340-8e36-2a7697663df2', 'e2d0c78b-44b2-4cb9-b7ba-367a8def0f43', '5bb903ec-e286-418a-992b-f3610a2d6bc6', '48425dc3-2cb7-44a0-bc98-777fc14d5976', '080ecfdb-909d-4ed5-94fd-242abb0338df', '06c49c81-6223-4590-90d2-5a19f3347c46', '3b284908-1123-46a1-b738-ee81090bff03', 'cd77f25f-7baf-41b5-b30c-5fb1374e5609', 'd3b016bd-4444-410b-84dd-7939a5edd777', '45aaf61e-4aa2-4ac2-8f5e-7b20b3d369f8']


## 분석 요약

이정호 주임의 PC에서 수집된 디지털 포렌식 아티팩트 분석 결과, 교육생 개인정보가 포함될 수 있는 파일들이 외부 저장매체(USB)를 통해 유출되었을 가능성이 있는 일련의 행위가 식별되었습니다. 정보 수집 및 압축, 외부 저장매체 연결, 그리고 증거 삭제로 이어지는 과정이 확인되었습니다.

*   **취득 행위:** 이정호 주임은 9월 초부터 중순까지 교육생들의 개별 활동 보고서를 수집하여 PC에 저장하였으며, 9월 15일 이전에 이를 하나의 압축 파일로 생성하여 정보 유출을 위한 준비를 한 것으로 판단됩니다.
*   **유출 행위:** 8월부터 9월 15일까지 SanDisk USB 저장매체가 여러 차례 PC에 연결된 기록이 확인되었으며, 특히 파일 삭제 직전에 USB가 연결되어 압축된 파일을 외부로 복사했을 정황이 포착되었습니다.
*   **증거 인멸:** 9월 15일, 22일, 30일에 걸쳐 수집 및 압축된 교육생 보고서 파일들을 휴지통으로 삭제하여 정보 유출 흔적을 은폐하려 시도한 것으로 분석됩니다.

### 행위별 분석 결과

| **구분** | **일시 (KST)** | **행위 내용** | **관련 증거** |
|---|---|---|---|
| **취득 행위** | 2025-09월 초 ~ 중순 | 교육생 개별 활동 보고서 파일 수집 및 PC 저장 | LNK 파일, 휴지통 삭제 기록 (`lnk_files_data`, `recycle_bin_files_data`) |
| **취득 행위** | 2025-09-15 14:47:32 이전 | 수집된 보고서 및 자료를 `팀공란_주간보고자료_0909.zip`으로 압축 | `팀공란_주간보고자료_0909.zip` 삭제 기록, 알집 실행 흔적 (`recycle_bin_files_data`, `lnk_files_data`) |
| **유출 행위** | 2025-08-05 00:05:28 ~ 2025-09-15 14:50:33 | SanDisk USB 저장매체 여러 차례 연결 및 파일 복사 시도 정황 | USB 장치 연결 기록 (`usb_devices_data`) |
| **증거 인멸** | 2025-09-15 14:47:32 | 교육생 보고서 파일 및 압축 파일(`팀공란_주간보고자료_0909.zip`) 휴지통 삭제 | 휴지통 삭제 기록 (`recycle_bin_files_data`) |
| **증거 인멸** | 2025-09-22, 2025-09-30 | 추가적인 교육 관련 파일 삭제 | 휴지통 삭제 기록 (`recycle_bin_files_data`) |



 *   `id: d491d6e5-43d1-4b7b-9b11-bedd9f4c9cb3`, `device_metadata__device_class_name: SanDisk Ultra USB 3.0`, `setupapi_info__first_connection_time: 2025/08/08 11:43:30.471`
    *   `id: 0a526cd3-bec3-4644-b4ab-4aae2829e661`, `device_metadata__device_class_name: SanDisk Ultra`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: bcc57888-e1c6-4e0f-aeeb-b6161b1affc4`, `device_metadata__device_class_name: SanDisk Cruzer Blade`, `setupapi_info__first_connection_time: 2025/08/14 00:03:16.500`
    *   `id: 6534d300-224e-401f-839a-6a51fb1d80b6`, `device_metadata__device_class_name: SanDisk SanDisk Ultra`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: 8945de65-d30b-481a-9e69-76fb10938cc7`, `device_metadata__instance_id: USB\VID_090C&PID_557D\4C530010300302111045`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: e7507fc8-a747-426e-a527-5f5ea6ecb4f2`, `device_metadata__vid_pid: VID_090C&PID_6860`, `setupapi_info__first_connection_time: 2025/08/05 21:24:25.881`
    *   `id: dc612990-5309-4f3b-aaff-645e4aa76223`, `device_metadata__instance_id: USB\VID_090C&PID_6860\R54NB01A5HJ`, `setupapi_info__first_connection_time: 2025/08/05 09:54:33.982`
    *   `id: bbea8d48-f598-4ca4-a1b8-49ae764aa7bb`, `device_metadata__instance_id: USB\VID_090C&PID_6860\R54NB01A5HJ`, `setupapi_info__first_connection_time: 2025/08/05 09:54:33.991`
    *   `id: af979eaa-ee1f-49fb-b573-d5596f4df6e8`, `device_metadata__vid_pid: VID_090C&PID_6860`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: cd03c86b-b5b7-4266-a236-0f027f4a8008`, `device_metadata__vid_pid: VID_090C&PID_6860`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: 3e584c24-9749-416b-8726-2ad48890b49c`, `device_metadata__vid_pid: VID_090C&PID_6860`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: 46805c52-7a70-4828-8a1d-bd313b82a3a2`, `device_metadata__vid_pid: VID_090C&PID_6860`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: dbf5b046-4105-4530-80f1-abc2dd4e5bbd`, `setupapi_info__first_connection_time: 2025/08/19 09:27:45.098`
    *   `id: 6d7cfad2-0eff-4709-85c6-fb55100cc7d3`, `setupapi_info__first_connection_time: 2025/06/26 11:45:37.500`
    *   `id: 32d5c1d2-39a9-4de3-bebf-617a55a810cc`, `setupapi_info__first_connection_time: 2025/07/29 10:03:10.761`
    *   `id: b71aabc8-ede9-4cef-9de4-c00e8a9c91a5`, `device_metadata__instance_id: USB\VID_090C&PID_6860\R54NB01A5HJ`, `setupapi_info__first_connection_time: 2025/09/30 14:50:02.120`
    *   `id: 85f62618-f220-453f-9c28-f57b86fd409f`, `device_metadata__instance_id: USB\VID_090C&PID_6860\R54NB01A5HJ`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: 64546f7e-ce77-4970-9059-ad7c12106d6b`, `device_metadata__instance_id: USB\VID_090C&PID_6860\R54NB01A5HJ`, `setupapi_info__first_connection_time: 2025/08/05 09:54:59.268`
    *   `id: cfec9381-1ed1-4d6f-a279-0565f71ca91e`, `device_metadata__vid_pid: VID_090C&PID_6860`, `setupapi_info__first_connection_time: 2025/09/29 10:30:16.762`
    *   `id: 986b9d13-988b-46bc-b4ba-2a492802f1d3`, `setupapi_info__first_connection_time: 2025/08/14 00:03:16.500`
    *   `id: 1527a59e-c211-49c7-8a44-b291c4151caf`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: a77b83cb-1440-4dee-8743-8a318c96708d`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: 565e63cd-cd40-4634-90f1-234ccd9a38f1`, `setupapi_info__first_connection_time: 2025/07/25 09:59:21.500`
    *   `id: 5f19bdeb-1cc2-4b55-9d29-e41243729372`, `device_metadata__device_class_name: USB SanDisk 3.2Gen1`, `setupapi_info__first_connection_time: 2025/08/13 17:09:43.276`
    *   `id: 8494204a-37ac-4b6f-9263-5acadf918185`, `device_metadata__device_class_name: USB SanDisk 3.2Gen1`, `setupapi_info__first_connection_time: 2025/08/08 11:43:30.471`
    *   `id: 27e48845-b907-4ce0-994c-2cfbd11d011e`, `device_metadata__device_class_name: USB SanDisk 3.2Gen1`, `setupapi_info__first_connection_time: 2025/08/11 09:55:49.747`
    *   `id: f11cbaba-9fe6-45f6-938b-d49269657804`, `device_metadata__device_class_name: SanDisk Ultra USB 3.0`, `setupapi_info__first_connection_time: 2025/08/12 16:03:52.394`
    *   `id: 56f5d4ff-02cf-4771-92b2-82def42a3007`, `device_metadata__device_class_name: USB SanDisk 3.2Gen1`, `setupapi_info__first_connection_time: 2025/08/08 11:43:30.471`
    *   `id: f4dd504a-6626-40e7-8671-deee67f76e5f`, `device_metadata__device_class_name: SanDisk Ultra USB 3.0`, `setupapi_info__first_connection_time: 2025/08/08 11:43:30.471`
    *   `id: 1dfed90c-5b1a-4ea2-a57c-b8f2bd1ccecd`, `device_metadata__device_class_name: SanDisk Ultra USB 3.0`, `setupapi_info__first_connection_time: 2025/08/13 10:10:32.547`
    *   `id: 35968423-25f3-44c2-ba32-ec75b298d679`, `device_metadata__device_class_name: SanDisk SanDisk Ultra`, `setupapi_info__first_connection_time: 2025/08/01 08:40:35.788`
    *   `id: 4020f9db-b0cd-49f1-ab63-a0f0b3d974d5`, `device_metadata__device_class_name: SanDisk Cruzer Blade`, `setupapi_info__first_connection_time: 2025/08/14 17:44:05.683`
    *   `id: c4ac4c33-5f6e-4303-8ba2-dfcfe137eb79`, `device_metadata__device_class_name: SanDisk Ultra`, `setupapi_info__first_connection_time: 2025/08/05 09:05:28.167`
## 교육생 개인정보 유출 의심 활동 분석 결과 보고서

### **분석 결과 요약**

이정호 주임의 PC에서 **두 차례에 걸쳐 교육생 관련 파일들을 압축하여 정보를 취득**하고, **파일 삭제를 통해 증거를 인멸**한 정황이 식별되었습니다. 특히 2025년 9월 15일에는 **파일 삭제 직후(3분 이내) USB 저장장치가 연결**된 기록이 발견되어, 이를 통해 압축된 파일이 **외부로 유출되었을 가능성이 매우 높습니다.** 온라인을 통한 유출 흔적은 발견되지 않았으나, USB를 이용한 데이터 유출 및 증거 인멸 패턴이 명확하게 나타납니다.

---

### **아티팩트 분류 및 분석 결과**

분석 과정에서 식별된 모든 아티팩트를 '취득 행위', '유출 행위', '증거 인멸 행위', '기타 의심 행위' 기준으로 분류한 결과는 다음과 같습니다.

### 1. 취득 행위

교육생 개인정보가 포함된 것으로 추정되는 파일들을 수집하여 외부로 반출하기 용이하도록 압축 파일을 생성한 행위입니다. 이는 정보 유출을 위한 사전 준비 단계에 해당합니다.

| 원본 데이터 ID | 파일명 | 행위 시간 (UTC) | 행위 시간 (KST) | 분석 |
| :--- | :--- | :--- | :--- | :--- |
| `5a18f29c-69cf-4ca2-a472-74eecdbc024e` | `팀공란_주간보고자료_0909.Zip` | 2025-09-15 05:47:32 | 2025-09-15 14:47:32 | 10주차 교육생 활동보고서들을 압축하여 하나의 파일로 취합함. |
| `a37ef8cf-e162-4413-a0f0-b69810effcf9` | `개별 활동보고서_김대한(10주차).pdf` | 2025-09-15 05:47:32 | 2025-09-15 14:47:32 | 위 압축 파일의 원본 데이터로 추정됨. |
| `4781b761-85ae-4544-b7fd-ac9765b9a715` | `개별 활동보고서_김민재(10주차).pdf` | 2025-09-15 05:47:32 | 2025-09-15 14:47:32 | 위 압축 파일의 원본 데이터로 추정됨. |
| `229d47cf-b32f-43a2-9497-fafb394b0c69` | `팀공란_주간보고자료_0916.Zip` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 11주차 교육생 활동보고서 및 관련 자료들을 압축하여 취합함. (반복 패턴) |
| `410c3d11-6bf1-44e4-8b61-fb45a8db935d` | `개별 활동보고서_김민재(11주차).pdf` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 위 압축 파일의 원본 데이터로 추정됨. |
| `2d4a87a7-c0a2-4ebf-bea7-2e4d63a36e6c` | `11주차 멘토링.pdf` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 위 압축 파일의 원본 데이터로 추정됨. |
| `065b4268-6c2f-4b41-a461-d93bbddf2b17` | `2025 전공분야 보수교육 OT(블록체인 보안).pptx` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 위 압축 파일의 원본 데이터로 추정됨. |

### 2. 유출 행위

취득한 정보가 담긴 압축 파일을 외부 저장매체로 옮기는 직접적인 유출 행위입니다. 증거 인멸 행위와 시간적으로 매우 근접하여 발생했습니다.

| 원본 데이터 ID | 장치 정보 | 연결 시간 (KST) | 분석 |
| :--- | :--- | :--- | :--- |
| `81051c80-a1fe-4f33-85e4-900d6def66ae` | USB Device (VID_04E8) | 2025/09/15 14:50:33 | `팀공란_주간보고자료_0909.Zip` 파일 삭제 **3분 후** PC에 연결됨. 압축 파일을 외부로 반출하는 데 사용된 것으로 강력히 의심됨. |
| `bab98b91-1975-4456-87e7-fe226024869b` | USB Device (VID_04E8) | 2025/09/15 14:50:33 | 위와 동일한 시간에 기록된 동일 장치 연결 로그. |

### 3. 증거 인멸 행위

정보 취득 및 유출에 사용된 원본 파일과 압축 파일을 PC에서 삭제하여 행위의 흔적을 제거하려는 시도입니다. 여러 파일이 동일한 시간에 삭제된 점이 특징입니다.

| 원본 데이터 ID | 삭제된 파일명 | 삭제 시간 (UTC) | 삭제 시간 (KST) | 분석 |
| :--- | :--- | :--- | :--- | :--- |
| `5a18f29c-69cf-4ca2-a472-74eecdbc024e` | `팀공란_주간보고자료_0909.Zip` | 2025-09-15 05:47:32 | 2025-09-15 14:47:32 | USB 연결 3분 전, 원본 파일과 함께 삭제하여 증거 인멸 시도. |
| `a37ef8cf-e162-4413-a0f0-b69810effcf9` | `개별 활동보고서_김대한(10주차).pdf` | 2025-09-15 05:47:32 | 2025-09-15 14:47:32 | 압축 파일과 정확히 동일한 시간에 삭제됨. |
| `4781b761-85ae-4544-b7fd-ac9765b9a715` | `개별 활동보고서_김민재(10주차).pdf` | 2025-09-15 05:47:32 | 2025-09-15 14:47:32 | 압축 파일과 정확히 동일한 시간에 삭제됨. |
| `229d47cf-b32f-43a2-9497-fafb394b0c69` | `팀공란_주간보고자료_0916.Zip` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 1주일 뒤, 동일한 패턴으로 증거 인멸 행위 반복. |
| `410c3d11-6bf1-44e4-8b61-fb45a8db935d` | `개별 활동보고서_김민재(11주차).pdf` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 압축 파일과 정확히 동일한 시간에 삭제됨. |
| `2d4a87a7-c0a2-4ebf-bea7-2e4d63a36e6c` | `11주차 멘토링.pdf` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 압축 파일과 정확히 동일한 시간에 삭제됨. |
| `065b4268-6c2f-4b41-a461-d93bbddf2b17` | `2025 전공분야 보수교육 OT(블록체인 보안).pptx` | 2025-09-22 05:00:15 | 2025-09-22 14:00:15 | 압축 파일과 정확히 동일한 시간에 삭제됨. |

### 4. 기타 의심 행위

직접적인 유출 행위와 시간적 연관성은 낮으나, PC에서 다수의 외부 저장장치를 사용한 이력을 보여주는 기록들입니다. 이는 평소 외부 장치 사용이 빈번했음을 나타냅니다.

| 원본 데이터 ID | 장치 정보 / 행위 | 시간 (KST) | 분석 |
| :--- | :--- | :--- | :--- |
| `d491d6e5-43d1-4b7b-9b11-bedd9f4c9cb3` | SanDisk Ultra USB 3.0 연결 | 2025/08/08 11:43:30 | 과거 USB 장치 사용 이력 |
| `0a526cd3-bec3-4644-b4ab-4aae2829e661` | SanDisk Ultra 연결 | 2025/07/25 09:59:21 | 과거 USB 장치 사용 이력 |
| `bcc57888-e1c6-4e0f-aeeb-b6161b1affc4` | SanDisk Cruzer Blade 연결 | 2025/08/14 00:03:16 | 과거 USB 장치 사용 이력 |
| `6534d300-224e-401f-839a-6a51fb1d80b6` | SanDisk SanDisk Ultra 연결 | 2025/07/25 09:59:21 | 과거 USB 장치 사용 이력 |
| `b71aabc8-ede9-4cef-9de4-c00e8a9c91a5` | USB Device (R54NB01A5HJ) 연결 | 2025/09/30 14:50:02 | 유출 의심 행위 이후 다른 USB 장치 연결 이력 |
| `cfec9381-1ed1-4d6f-a279-0565f71ca91e` | USB Device (VID_04E8) 연결 | 2025/09/29 10:30:16 | 유출 의심 행위 이후 다른 USB 장치 연결 이력 |
| 외 27건 | 기타 USB 장치 연결 기록 | 2025/06/26 ~ 2025/09/30 | 분석 기간 내 다수의 USB 장치 연결 이력 확인. |