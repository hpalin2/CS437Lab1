# PiCar-X Development notes:

I Currently have gotten the model to load but I am having trouble with OpenCV. It seems it doesn't recognize my camera, so it won't capture frames. I recommend looking into picamera2, or finding the pathing for the camera I don't believe it is video0. This is due to how raspberry pi has switched camera stack so there isn't many resources on how to use it. So current script doesn't work. I built the diagnose script to help test different methods to get the camera to work.

The username to this pi is hpalin, for password ask me and I'll text it to you.

Make sure you connect to wifi from shell. You can do CTRL+ALT+F2 to get to shell and skip desktop.
Mapping I haven't looked into enough and doesn't seem to work.

To scan for the pi on your network to ssh use this command based on ur ip:

nmap -sn 192.168.68.0/22

Then scan those ips that are on the network:

nmap -p 22 192.168.68.1 192.168.68.51 192.168.68.53 192.168.68.54 192.168.68.59 192.168.68.60 192.168.68.62 192.168.68.64 192.168.68.65 192.168.68.76 192.168.68.81 192.168.68.83 192.168.68.85 192.168.68.87 192.168.68.92 192.168.71.249 192.168.71.250

Only one should be open to ssh add the key I will email to you:

ssh-add rasp-key

Then ssh in:

ssh hpalin@192.168.68.78