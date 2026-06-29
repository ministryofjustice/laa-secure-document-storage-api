# Open Policy Agent (OPA) Files
Only expected to work locally on Mac. To see OPA integration working:


1. Make sure `opa-python-client` package has been included in the pipenv environment (update environment with `pipenv sync`).
2. Run `docker commpose up` as usual for SDS. `docker-compose-yaml` has now been updated to also start an OPA Docker container, accessible via `localhost:8181`.
3. (Optional) Set environment variables `OPA_HOST` and `OPA_PORT` which are used by the SDS application to identify the OPA server. Not essential as SDS defaults to using `localhost` and `8181` respectively.
4. Use the `/get_file_details` endpoint, which has been modified to apply the above OPA rule and display a log message with the related outcome, e.g. `{"event": ">>>>> Filename: necronomicon, OPA 'file is unrestricted' result: {'result': False}`.

**Sanity check** - open `http://localhost:8181/` in browser and look for OPA version message.

### Alternative - run OPA binary locally
It's also possible to run OPA locally instead of the dockerised version. This can be done as follows:

1. Install OPA (e.g. `brew install opa`)
2. Change directory to the present directory (`./opa`)
3. Start OPA using `opa run --server detect_thoughtcrime.rego`