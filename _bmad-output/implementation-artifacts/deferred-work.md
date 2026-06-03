# Deferred Work

## Deferred from: code review of 1-6-관리자-웹-페이지-pdf-업로드-ui (2026-06-03)

- W1: 폴링 첫 tick이 2초 후라 백엔드가 즉시 완료해도 최대 2초 지연 표시 — 경미한 UX 갭. 업로드 완료 직후 즉시 status 체크를 원할 경우 `setInterval` 대신 `setTimeout` 체이닝 방식으로 변경하거나 POST 응답 직후 한 번 즉시 status 조회 추가.
