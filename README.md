⚙️ Installation Steps

```bash
pkg update && pkg upgrade -y
pkg install python git -y
rm -rf Facebook-Tool
git clone --depth=1 https://github.com/OneManCodeReturn/Facebook-Tool
cd Facebook-Tool
pip install -r requirements.txt
termux-setup-storage
python Meta.py
