# old_config Files

This folder holds config files that were used before PR #504 applied. These files rely on having "general config" files in `/Authz` directory ratther than in the client config repo.

These files have been preserved in case the PR #504 changes need to be reversed. 

Restoring these files to their original locations should restore the previous config behaviour. This can be done by copying them all to the root of SDS in their existing sub-folders and overwriting existing files.

Note some of the file are hidden (`./.gitignore/` and `.env.sample`) so only show using likes of `ls -a` or `command-shift-.` in Finder.

Note these folders and files can be deleted if PR #504 is successful!