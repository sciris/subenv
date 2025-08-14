# Subenv

Python package that lets you run multiple versions of code in parallel in a single interpreter session via virtual environments. Example:

```py
import subenv

# Paths to Python interpreters (e.g. different conda, uv, or venv environments)
OLD = "/old/starsim/env/bin/python"
NEW = "/new/starsim/env/bin/python"

# Create the environments
env_old = subenv.Env(OLD)
env_new = subenv.Env(NEW)

cmd1 = "import starsim as ss"
env_old.exec(cmd1)
env_new.exec(cmd1)

cmd2 = "res = ss.Sim().run().results"
env_old.exec(cmd2)
env_new.exec(cmd2)
res_old = env_old.get('res')
res_new = env_new.get('res')

print("old:", res_old)
print("new:", res_new)

env_old.close()
env_new.close()
```