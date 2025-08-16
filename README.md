⚙️ Installation Steps

```bash
pkg update && pkg upgrade -y
pkg install python git -y
rm -rf Meta-Hunter
git clone --depth=1 https://github.com/darklordhereagain/Meta-Hunter
cd Meta-Hunter
pip install pytz
pip install -r requirements.txt
termux-setup-storage
python Meta.py
