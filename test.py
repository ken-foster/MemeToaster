
import os

path = os.path.join(os.getcwd(), "version.txt")
with open(path,"r") as f:
    version = f.read()

print(version)