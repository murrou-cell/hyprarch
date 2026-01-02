# wget https://download.cdn.viber.com/desktop/Linux/viber.AppImage
# chmod +x viber.AppImage
# extract to /opt
sudo mkdir -p /opt/viber
sudo wget -O /opt/viber/viber.AppImage https://download.cdn.viber.com/desktop/Linux/viber.AppImage
sudo chmod +x /opt/viber/viber.AppImage
cd /opt/viber && sudo /opt/viber/viber.AppImage --appimage-extract
# create symlink
sudo ln -s /opt/viber/squashfs-root/usr/bin/Viber /usr/local/bin/Viber
