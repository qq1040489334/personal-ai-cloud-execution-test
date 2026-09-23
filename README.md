# personal-ai-cloud-execution-test

Isolated experiment for `PERSONAL_AI_CLOUD_EXECUTION_GOLDEN_TEST_01`.

Goal: verify a complete development loop in a cloud environment:
GitHub repo -> cloud environment -> OpenCode agent -> code change -> tests -> commit -> evidence.

Nothing here is part of PersonOS, Knowledge, or any real project. This is a
throwaway sandbox.

## Run tests

```powershell
python -m pytest test_hello.py -q
```
