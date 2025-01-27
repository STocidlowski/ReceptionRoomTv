#RaspberryPi #Linux #Python

# Waiting Room TV Project

Transform your Raspberry Pi into a standalone video loop player for waiting rooms, offices, or any space that needs a 
simple, cost-effective video playback solution. This is designed to boot up and play videos in a loop without streaming.

I started this project 12/2024, later expanded it to 4 TVs in an urgent care office 1/2025. This project is based on the 
[Desktop Simpsons TV project](https://withrow.io/simpsons-tv-build-guide). This project is running without issue on a 
[Raspberry Pi Zero 2](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) ($15), however this can be run in any
environment, bonus points if you reduce ewaste by reusing an idle machine. I wanted to reduce E-waste throwing out these older boards.

The goal was a standalone video player that will run at boot. This was done to play videos in a loop on a waiting room
TV, and does not need the extreme bandwidth of continuous streaming.

Plan to use a large SD card (128GB, 256GB) if you are loading the videos permanently, otherwise use a small SD card 
(8+GB) and load from a larger USB.


## Prerequisites
- Hardware:
  - [Raspberry Pi Zero 2 W](https://www.adafruit.com/product/5291) - $15.00
  - [USB Power Only Cable with Switch](https://www.adafruit.com/product/2379) - $5.95
  - [Mini HDMI to HDMI Cable](https://www.adafruit.com/product/2775) - $5.95
  - Micro SD card (8GB+ recommended)
- Software:
  - Raspberry Pi OS
  - Tools: Handbrake or FFMPEG for video encoding


#  Video Encoding

Install [handbrake](https://handbrake.fr/) to re-encode your files if you want/need to. 

Videos must be encoded into the H.264 format, Raspberry Pis do not have the dedicated hardware processing for H.265/HEVC

I converted to 720p with burned in subtitles. I may redo this later, as MPV is very capable of displaying subtitles.

FFMPEG also works if you prefer/know that. Ex: `ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset fast output.mp4`

# Raspberry Pi settings

Install Raspberry Pi OS using [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on to your SD card

As with any new install, update everything
```bash
sudo apt update
sudo apt upgrade -y
```
Change some settings here, like expanding the filesystem, changing the name, etc:
```bash
sudo raspi-config
```

You should set up SSH key, and disallow any password logins.

I am doing this from Windows, so I am using [PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/) as a SSH client. You can generate the SSH Key in PuTTY-Gen. Save the key safely, use it in PuTTY to log in automatically.

Use open-ssh to generate the key if you are in a linux environment.

# Preparation / Security

Secure your access if you expose the project to the internet. You can even disable wifi after the project is done
If you have external access, port forwarding or dynamic DNS, Fail2Ban or the like, otherwise you are probably contributing 
to a botnet. 

The following optional section is because I want to access the project from my computer from anywhere.

## Tailscale (Optional)
I personally installed [Tailscale](https://tailscale.com), because "it just works." Useful since I may want to update/make 
changes from home. Now I can expose the project to the internet, and SSH from any of my devices.
Use the Tailscale admin page to add a Linux server, and will automatically generate an installation script.

```bash
curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up --auth-key=tskey-auth-.....
```

Enable automatic updating of tailscale:
```bash
sudo tailscale set --auto-update
```

Enable UFW (firewall) to only allow SSH access from your tailnet.
```bash
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0 to any port 22
sudo ufw enable
sudo ufw status
```


## Remove the boot text on reset (optional):
```bash
sudo nano /boot/firmware/cmdline.txt
```
remove `fsck.repair=yes`
add `consoleblank=0 logo.nologo quiet splash` to the end

## Xserver install (may not be needed, not sure)
Ensure xserver is Installed, since no desktop is installed.
```bash
sudo apt-get install xserver-xorg x11-xserver-utils
```

```bash
echo "export XDG_RUNTIME_DIR=/run/user/$(id -u)" >> ~/.bashrc
```

## Video player install
Install the video player [MPV](https://mpv.io) 
```bash
sudo apt-get install mpv -y
```

## Install GIT 
Install git, otherwise you will need to just copy player.py directly and create a 'videos' folder
```bash
sudo apt-get install git -y
```

# Script Installation

Clone this repository, or fork it and change the directory names first. (I use "shawn" as the user directory, you can use "pi", or dl it somewhere else) 

If you don't want to use git, just copy player.py itself and create a videos folder

```bash
git clone https://github.com/STocidlowski/ReceptionRoomTv
```

Setup the tvplayer service:
```bash
sudo nano /etc/systemd/system/tvplayer.service
```

Paste the following into the editor (change `shawn`, to your username), and save:
```systemd
[Unit]
Description=ReceptionRoomTv
After=network.target

[Service]
WorkingDirectory=/home/shawn/ReceptionRoomTv/
ExecStart=/usr/bin/python /home/shawn/ReceptionRoomTv/player.py
Restart=always
Environment=DISPLAY=:0
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```


Now lets set these two services to start on boot:

```
sudo systemctl enable tvplayer.service
```

if you edit, and need to reload use:
```bash
systemctl daemon-reload
```


## Set up USB Access

We should allow every user to access USB. Edit the file:
```bash
sudo nano /lib/systemd/system/systemd-udevd.service
```

Scroll down to where it says **PrivateMounts=yes** and change it to:
```
PrivateMounts=no
```

### Solution 1 (Auto mounting of any usb drive on boot): 
```bash
sudo nano /etc/fstab
```

Automatic mounting of USB Drives (on boot, not hot swaping):
Add the following to the end of the file
```
/dev/sda1 /mnt/usb auto nosuid,nodev,nofail 0 0
/dev/sdb1 /mnt/usb1 auto nosuid,nodev,nofail 0 0
```


### Solution 2 (using same drive, allowing that drive only)
"blkid" will list all the blocks, including any USB drives inserted. Write down the UUID of the drive you want to mount
```bash
sudo blkid
```

`/dev/sda1: UUID="8227-A56F" BLOCK_SIZE="512" TYPE="vfat" PARTUUID="d92dc72c-01"`

`/dev/sdb1: LABEL="SANDISK32" UUID="2C67-8722" BLOCK_SIZE="512" TYPE="vfat" PARTUUID="f95ccdef-01"`

if you want to temporarily test if mounting the usb works (needed every reboot):
```bash
sudo mount /dev/sda1 /mnt/usb1
```

Added the following line:
```bash
UUID=8227-A56F /mnt/usb1 vfat defaults 0 0
```

## Final Steps

```
sudo shutdown -r now
```

After restarting your Raspberry Pi, the video player should start automatically. If everything works as expected, the 
setup is complete!


## Copy video files from the USB (optional)
If you want to, and if your SD card is large enough for it.

```
sudo cp -R /mnt/usb1 ~/ReceptionRoomTv/videos
```


