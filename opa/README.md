# Open Policy Agent (OPA) Files
Only expected to work locally on Mac.

For OPA integration to work need to:
1. Install OPA (`brew install opa`)
2. Change directory to the present directory
3. Start OPA using `opa run --server detect_thoughtcrime.rego`
4. Make sure `opa-python-client` package has been included in the pipenv environment.
5. (Optional) Set environment variables `OPA_HOST` and `OPA_PORT` but service defaults to `localhost` and `8181` respectively, the defaults for OPA server.

The `/get_file_details` endpoint has been modified to apply the above OPA rule.

Potential improvement would be to use Dockerised version of OPA which is launched as part of our standard docker-compose file.