
# edit the ip address
cd frontend-chat/src
nano App.vue

const response = await fetch('http://13.125.205.137:8000/chat'), 
(Make sure you keep the :8000 port).
Save and Exit: Ctrl+O, Enter, Ctrl+X.

Bash
```bash
lsof -i :5173
```
(You will see a number like 23456 under the PID column).

Kill it:
code
Bash
kill -9 13910 13912

# Start it again in the background:
code
Bash
cd ~/model/eonehealthcare/frontend-chat
nohup npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &

check logs:
```bash
tail -f frontend.log
```

# Step 2: Install the Venv Tool
sudo apt update
sudo apt install python3-venv -y

python3 -m venv eone

source eone/bin/activate
pip install --upgrade pip
pip install -r requirement.txt

nohup python3 main.py > backend.log 2>&1 &

lsof -i :8000


# The Fix: Import the Microsoft GPG Key
* 1. Download and install the Microsoft GPG key
curl -sLS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /usr/share/keyrings/microsoft-prod.gpg > /dev/null

* 2. Update your package lists again
sudo apt-get update

* 3. Install the ODBC Driver
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Step 4: Run Streamlit

```bash
cd ~/Documents/drprompt-ui
nohup streamlit run Chat.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &
```

# AWS server git
If you are 100% sure you don't need any local changes on the server, you can force the local branch to match the remote exactly.
```bash
git fetch origin main
git reset --hard origin/main
```

BASE_URL = "http://127.0.0.1:8000"



```bash
# 1. Download the latest changes from GitHub (but don't merge them yet)
git fetch origin

# 2. Overwrite ONLY the specific file with the version from the 'main' branch
git checkout origin/main -- drprompt/Chat.py
```