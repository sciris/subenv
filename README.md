# Subenv

Python package that lets you run multiple versions of code in parallel in a single interpreter session. Example:

```py
import subenv

OLD = "/old/starsim/env/bin/python"
NEW = "/new/starsim/env/bin/python"

# Run in NEW env (current process can be anywhere)
s_old = subenv.Env(OLD)
s_new = subenv.Env(NEW)

cmd1 = "import starsim as ss"
s_old.exec(cmd1)
s_new.exec(cmd1)

cmd2 = "res = ss.Sim().run().results"
s_old.exec(cmd2)
s_new.exec(cmd2)
res_old = s_old.get('res')
res_new = s_new.get('res')

print("old:", res_old)
print("new:", res_new)

s_old.close()
s_new.close()
```