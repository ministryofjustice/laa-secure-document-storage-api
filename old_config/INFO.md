# old_config Files

This folder holds config files that were used before PR #504 applied. These files rely on having "general config" files in `/Authz` directory ratther than in the client config repo.

These files have been preserved in case the PR #504 changes need to be reversed. 

Restoring these files to their original locations does most of the things to restore the config behaviour. This can be done by copying them all to the root of SDS in their existing sub-folders and overwriting existing files.

Note some of the file are hidden (`./.gitignore/` and `.env.sample`) so only show using likes of `ls -a` or `command-shift-.` in Finder.

Note these folders and files can be deleted if PR #504 is successful!

### Aditional Change
Restoring these old files is not quite sufficient as the hard-coded default values for `CONFIG_DIR` also need updating in `src/services/client_config_service.py`

Two lines with 

```config_dir = os.getenv('CONFIG_DIR', '/app/configs')```

neet to be changed to 
```config_dir = os.getenv('CONFIG_DIR', '/app/clientconfigs')```

### Another thing needed for old config to work
In our orginal config file setup, our Cloud Platform environments rely on GitHub environment variables, set manually via GitHub front-end, for `CASBIN_POLICY` and `CASBIN_MODEL`. These need to be in place for the old type of config setup to work. These have NOT been deleted as part of PR #504 changes, so should still exist to enable to old process to still work. These can be viewed in GitHub via the `Settings` tab, then `Environments` in the side bar.