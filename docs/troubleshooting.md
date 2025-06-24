# Troubleshooting during development or running of SDS API

## 401 Unauthorised

This can be for several reasons:

* No authentication has been provided
* The token may have expired
* The scope may not match the SDS instance.

In all cases, check the logs for more information.

## 403 Forbidden (running in environment)

If the body of the message is HTML, then the 403 is from nginx, which means the border is blocking the request before
it gets to the SDS API. Try refreshing your VPN connection, or otherwise check the status of the Cloud Platform
environment.

If the body is a string "Forbidden" or JSON with `"detail": "Forbidden"` then the rejection is from the SDS API, which
means the client has insufficient permissions. Check the client you are using is in the official clientconfigs
repository, and that the route you are requesting is allowed in the client ACL.


## 403 Forbidden (running locally)

Run `docker compose logs sds-api`

If you see `{"event": "Loaded 1 policy files", "logger": "src.utils.multifileadapter" ...}` then the client
configurations have not been found. Ensure the client configurations to be used are present in `./clientconfigs`
(default repository settings).


## 500 Internal error

Usually during development, check the SDS logs :)
