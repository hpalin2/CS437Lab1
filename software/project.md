 IOT Lab 1: IoT Devices


DISCLAIMER: This lab looks long - do not worry! Most of this document is more like reading material than a lab. Our goal is to provide you with extensive descriptions, to walk you through each step, so you will not get stuck, and to also teach you additional things. It is ok to skip over parts of the reading if you feel comfortable and don't feel like you need the extra help. Please review the Frequently Asked Questions for both parts, as they address many common pitfalls.

Lab Overview

Modern cars are no longer just engines and tires. Inside of them are highly sophisticated computer networks, controlling and monitoring an array of sensors, machine learning and computer vision algorithms, performing mathematical computations to keep you and your passengers maximally safe in every contingency and danger that arises.

In this class, we will guide you to gain experience with Internet of Things devices. You will do this by implementing a 2021 Tesla Model S. In particular, you will be implementing a vehicular network, navigation systems, and computer vision infrastructure comparable to a simplified version of the 2024 Tesla Model S. To save on costs, we won't be building a life-sized car, we'll build something smaller (and simpler!). But don't be fooled though - your infrastructure will share several key capabilities with real car platforms, performing real-time communications within the automobile to perform life-saving features such as obstacle avoidance and lane departure mitigation. Doing this will give you experience in programming IoT components, as well as teach you about vehicular networks, an emerging powerful use case for IoT.

For many of you, this will be your first experience working with real hardware. This may make this lab assignment different from other labs/homeworks you've worked on in the past. A few things to keep in mind (a) Start early in this Lab since things can go wrong when you are interacting with the real world (with an ultrasonic sensor, etc.) (b) if you encounter a problem, try googling for it or searching for posts in the forums - some solutions are already online. Your efforts will be rewarded at the end of the lab with a confidence that you can build real things. 

Before implementing vehicular networks on a real car, an important step is prototyping. The common approach in the industry is to test with the intended workflow until we have enough confidence with the structure of the system, before starting to produce the hardware. Although a true vehicular network may contain more components in the architecture, for the purpose of this lab we will take a simplified approach, building one individual car prototype with a simplified degree of autonomy. 

Figure 1: What you will implement, system architecture view
Tasks You Will Perform In This Lab
Part 1:
Assemble the car chassis.
Explore the code. Familiarize yourself with the code dealing with the ultrasonic sensor, velocity sensor, etc. 
[Submission] Create a demo video and submit a report. Details of submission and grading rubric can be found in Part 1 Submission and Grading.

Part 2:
Start early on this part as you are required to construct a complicated system with multiple modules.
Construct advanced mapping leveraging proximity detection. You will leverage the ultrasonic sensor to receive distance data and build an advanced mapping algorithm. 
Provide object detection capability to the car. You will use OpenCV for image preprocessing and TensorFlow for object detection.
Provide routing capability to the car. Utilizing the advanced mapping algorithm, you will implement a navigation algorithm to route from a given starting point to a goal.
Build a fully self-driving car. You will integrate all parts from previous tasks and demonstrate that your car is fully self-driving.
[Submission] Create a demo video and submit a report. Details of submission and grading rubric can be found in Part 2 Submission and Grading.




IOT Lab 1: IoT Devices (Part 1)


Ok, now let's get started! In part 1, you will assemble the car, explore the Pycar code, and implement some naive mapping and routing.
Step 1: Chassis Assembly

A key step when constructing an IoT device is putting together its housing and physical assembly. Oftentimes this will be the last step in your design process, after you have fully thought through about the structure of what you want to build, its environment, and so on. But in this case, since we know what we're building, we'll start with this step.

If you have not already done so, make sure you did lab 0, which overviews what parts to purchase. 

To put together the car housing (chassis), as well as setting up the Raspberry Pi to function with it, please follow the guide found at this link. (backup link: https://m.media-amazon.com/images/I/C1Tq1JjfipS.pdf). You may also find these youtube videos helpful:

https://www.youtube.com/watch?v=7m1DLLG3A8s
(10 min tutorial on assembling the Picar)

https://www.youtube.com/watch?v=UiRb1SDpezY
(2 min video showing (tracking line, objection detection, keyboard controls)

The link above will walk you through how to install the Raspberry Pi operating system on it, but if you could use some additional instructions you can follow these:

https://docs.sunfounder.com/projects/picar-4wd/en/latest/preparation/installing_the_os.html

After you have flashed the image, insert the card into Raspberry Pi, and connect a monitor, mouse and a keyboard to the Pi via the HDMI and USB ports. The Raspbian OS would automatically be installed once you start the Pi. Now you will have a fully functional Linux system on your Pi, with Internet access via the Wi-Fi module. Note you don't have to specifically use the optional power adapter mentioned early, any USB-C connection with enough amps will keep the Pi powered on (it will give you warnings or not power on if it's not getting enough power).



To assist you through this process, we'll walk you through in more detail the steps of setting up the Raspberry Pi next.

Figure 2: Raspberry Pi with Camera installed.

Do not underestimate a Raspberry Pi - It’s cheap (~$40), but it’s a powerful computer for its size! Equipped with a Linux Distro (Raspbian), an HDMI port for Monitors, USB ports for mice and keyboards, an SD card as a disk, a camera interface, Wifi and Ethernet module, and 40 GPIO pins, Raspberry Pi allows you to quickly prototype your IoT network without much hassle. When you have set up the Raspberry Pi, you will have a fully functional Linux system on your Pi, with Internet access via the Wi-Fi module. We will be using it to control the car in various ways, but please keep it forever, as it can do so many amazing things beyond just what is described in this lab!

Helpful hints:

1. If you use a 64 GB microSD (or larger), please follow the instructions in this link to format the microSD with FAT32, instead of the step 2 in page 9 in the above guide. This is necessary because the SD Formatter will use exFAT which is not supported by the Raspberry bootloader.
2. The Raspberry Pi 4 has an HDMI port that you can use to connect it to a monitor if you have one. If you do not, Pages 20-21 of the above guide tells you how to install the Pi up in "headless" mode. Those instructions are ok, but here are easier ones:
First, download the imager from https://www.raspberrypi.org/downloads/
Then, run the imager. Follow the steps it provides to put the recommended OS onto your SD card.
The SD card should now have the OS - add an empty ssh file to the root of the SD card to enable ssh access.
Add a wpa_supplicant.conf file to the root of the SD card using the following instructions: https://www.raspberrypi.org/documentation/configuration/wireless/wireless-cli.md . Change the country code from US to your 2-letter ISO 3166-1 country code if not in the USA. Also change the ssid (name of your Wifi network - note this is case sensitive) and psk (your Wifi password) Sample file:

ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
ssid="WiFiName"
psk="WiFiPassword"
id_str="school"
priority=0
}


3. If you are unable to connect Raspberry Pi 5 via SSH, first, try using the Pi’s IP address instead of its hostname. Sometimes raspberrypi.local cannot be resolved on certain networks. If that doesn’t work:
Connect the Pi to a monitor and keyboard.
Open a terminal and run hostname -I to see its IP address.
Use that address to connect: ssh pi@<IP_ADDRESS> (for example, ssh pi@192.168.1.25).
You can also use the same IP for VNC access. If the Pi is not appearing on the network, confirm its Wi-Fi or Ethernet settings directly on the monitor.
	Note that some students have also reported that they had difficulties connecting 
	to pi on their home network but connecting to a dedicated router worked for
	them.

For our purposes, we will need to use a camera module, which is not part of the instructions in the link above. Formal mounting of the camera should not be necessary; folding the camera to face straight forward and applying tape would be sufficient. If you would like something a bit more solid, you can cut a slit on top of the PiCar and mount the camera through that slit. To ensure you have the camera mounted and oriented properly, please load a picture on your cell phone's screen, and hold it in front of the car where you think objects might reasonably appear when the car is driving around. Then, look at the frame of the camera and place a picture on your phone within the frame of the camera and see if your car detects it and reacts as expected, i.e. stopping and waiting for the person to pass. If needed, adjust the camera placement on top of the car so the car can "see" the road nice and well.

Here are a few screenshots of the assembled car from a few different angles -- take a look and do some sanity checks to make sure you assembled it properly:
               




The Raspberry Pi should be set up first, but after that, the chassis assembly and the routing/mapping logic (we'll get to these in later sections) can be done in parallel. Note that the picar-4wd library code includes functions and example scripts; use them as you see fit, and feel free to fiddle with the car’s config file for car motion. 


Figure 3: Mounting the ultrasonic sensor atop your smart car.



There are example scripts at the bottom of the setup pdf (keyboard_control.py, servo, etc) that can be run to ensure you’re assembling the chassis properly.

Step 2: Implement your design on a PCB

Note: Don't worry about getting this step perfect. The goal is to give you general experience with PCB design in case you need it for the future. Go through the steps and do your best. You should generally be able to get it working. If there is a box here and there that is a bit off we won't take off points for that. Get it generally working and you will get full credit.

Printed circuit boards (PCBs) are a massive part of just about every piece of electronic equipment that we have in our everyday lives. Almost every electronic device you can think of contains at least one PCB, including phones, computers, tablets, televisions, cars. Because PCBs utilize copper tracks rather than actual wires, boards are smaller and they are not as bulky, power usage is vastly reduced, reliability is improved, etc. Hence when you build real IoT devices you don't just connect wires into sockets like you've been doing, you might do that for prototyping, but to do things for real you build PCBs. In general IoT systems, most of the devices have at least one PCB in it. If the whole system is designed to become one product, such as smart cars, a large PCB might be in it to connect to all other components inside it. Using the PCB in devices or the whole system can make them smaller and more portable. The PCBs are also very durable and long-lasting. They can take a lot of damage such as heat, moisture, or even physical force, without breaking apart. This makes them ideal for use in areas that are hazardous to electronics. In addition, PCBs are very efficient and easy to repair.

So how is a PCB physically created? A PCB is an electronic board with metal circuits embedded in it that connect different components on the device. The mechanical structure is made up of an insulating material laminated between layers of conductors. These layers form the circuit board and connect to components that are soldered to the board. With this multi-layer design, PCB can connect to multiple components on a small board. That is why it is very popular in the industry these days. 

In this step, you will gain experience in using commercial-grade software to create a PCB design for your car platform. In particular, we want to build a PCB to connect all your components and raspberry PI together, which is similar to the role of the 4wd board. Rather than build another 4wd board, we want to build our own board that ONLY connects to our components and raspberry PI. For the submitted requirement, you need to include at least motors, photo-interrupter, battery and grayscale module. If you cannot find the footprint for your component, you can use different types of the same component, such as different types of battery holders in your design. You can also put a connector header on your PCB and mark the component it connects to aside it. You need to use a line to address which component link to which header in your design. We suggest you design it from the raspberry PI hat, which has basic pins that connect to raspberry PI.

As many PCB design tools can be found online, we recommend you use KiCAD, a free and open source PCB builder. KiCAD also has very active and growing community of users and contributors. Last but not the least, KiCAD is cross-platform compatible, which means it has Windows, Mac and Linux versions for different users. You can download KiCAD here. you can go through tutorials like this, associated with the official document, which helps you make a clear understanding on how to build a PCB on KiCAD. We also provide some steps to start with KiCAD:

After you download KiCAD, we can start a new project in KiCAD. Open a new project from the template. Choose the Raspberry PI HAT from system templates (Figure 4). Press OK to start the project.

Figure 4: Open a Raspberry PI HAT project on KiCAD to start building PCB

Next, open the schematic editor and import the footprints of all your components. This is the place where you see all the pins and wires in your PCB. You need to add all your components’ footprint in it and create pins on board to connect to it. You can download the footprints for your components on this website. A footprint defines the arrangement of pads and pins used to physically attach and electrically connect a component to a PCB. The PCB footprints usually include information such as copper and solder mask layout, silkscreen, mounting holes (where applicable) and reference pin. After you download the footprints, press A to add symbols that represent your components in the schematic editor. Wired all symbols together. Don’t forget to run the footprint assignment tool on the top toolbar to assign each of the symbols you insert into the schematic editor to its footprint. Figure 5 gives an example of the ultrasonic symbol wired with a 4-pin connector.


Figure 5: An example of ultrasonic wired with 4-pin connector

After finishing editing symbols and wired them together, you should have wired all components to the board. Next step is to arrange and design your board with components on it.  Open the PCB editor. This is where you can see the board. In the upper toolbar, use the tool “Update PCB with changes made to schematic”. This will make all your components and wires you put in the schematic editor show in PCB editor. Rearrange all components to make sure there is no overlap between components and wires.

Figure 6: The “Update PCB with changes made to schematic” button.

Finally, select “File” -> “Plot…” in the PCB editor. We want you to generate gerber files for us to view your result. The Gerber format is an open, ASCII, vector format for printed circuit board (PCB) designs. It is also an industrial-standard PCB description file. By providing this file we can see your PCB in KiCAD. Check “F.Mask”, “B.Mask” and “Edge.Cuts” and leave all other options as they are. Click “Plot”. Then select “Generate Drill Files…” then click “Generate Drill File” without changing anything. We now have each layer of our PCB into a gerber file. Close gerber file generator and PCB editor.
Figure 7: The checkbox of the Gerber generator you need to check to get all layers of Gerber files.

Check the gerber files by opening Gerber Viewer before you submit the gerber files. In the viewer, select “File” -> “Open Autodetected Files” and choose all gerber files you just created. Check each layer of your gerber files to make sure your wiring design and components layout are all correct. Figure 8 shows an example on how the Gerber files can be looked like.

Figure 8: An example of the Gerber files on final PCB design.

Now you have finished your PCB design. Usually the next step is to print out your PCB and buy all components, then assemble them. Since we already have Pycar, we don’t need to print our PCB out. But it is still good to practice it before next time you need a new PCB board somewhere else.
Step 3: Explore the Pycar Code


Figure 9: Example code provided with the Pycar library . Look through it and get a sense of what it does!

Now that you have built your car, it’s time to test it out and get familiar with the PiCar library (which can be downloaded here , see API documentation here). Please note that the links provided are specific to Picar-4WD. If you are using a different model, be sure to consult the appropriate code base for that model (e.g., Picar-X has installation instructions here). Before we get into too much programming, we think it will be helpful for you to kind of look over the code and get a sense of what it does and how it works. 

The first step will be to download the code. Make a copy of it on your Raspberry Pi and read over the documentation and codebase. You don't need to read everything, just skim over parts and get a sense of how things work. In particular, look under the doc folder with all the markdowns of each function and its descriptions. Or you can take a look at the code in the picar_4wd folder of the repository, particularly init.py.  That should contain all functions you need to complete the lab. We encourage you to also write your own sample script and try calling some of these functions, i.e. reading from the ultrasonic or making the motors spin. Play around with the functions and try making the car do different things.

Another helpful part of the codebase we strongly encourage you to read and run, to both verify that your assembly is correct and to get you comfortable with the library, are the examples. The various examples should thoroughly test the functionalities of the car and provide you with some reference when writing your own control script. 

First, try running the keyboard_control.py program and making sure it works. This is important since it tests all your motors are running in the right direction; if that is not the case, you could either take apart the car and move around the motors (a rather arduous process) or adjust the directions of the motors in the data/config file. We recommend you also walk through the code and make sure you understand the function calls being made in this script, and see if you can trace the function calls back up inside the code as far as you can, since the library offers us wrappers to manipulate the components. For example, when you call fc.forward, that actually leads to the actual outputs in the motors’ corresponding GPIO pins to be changed -- see if you can look through the code and understand how that happens.

The next script you should explore is ultrasonic.py, which is the script responsible for interfacing with the car’s ultrasonic sensor for distance measurements. More information on the ultrasonic module for the Raspberry Pi can be found here, but essentially what it does is send out a small pulse of sound and measure the time it takes for that sound to bounce off the object in front of it and return (similar to what bats do), and then uses that time and the speed of the sound to calculate distance. A lot of this is abstracted away for you, but it’s still good to know how it works. Look through the ultrasonic.py file and trace back the function calls as far as possible, and get familiar with measuring distance since you will need it in the mapping portion of your script.

The third component worth exploring is the servo, which is what the ultrasonic sensor is mounted on. The servo is a type of motor that allows you to precisely control its rotation, which makes it the perfect option for us to rotate our ultrasonic sensor when taking distance measurements. servo.py contains all the wrapper code for interfacing with the servo motor and setting the angles, but again, please trace the function calls and see how the actual component is manipulated. Experiment with these different scripts to get familiar with making the right function calls.

Once you have some comfort with the PiCar library and the abstractions it provides, you can begin writing your scripts! Some good first steps, to see how these different functions can fit together: try having your car go forward by a certain distance, or have your car drive forward until it detects an object within 10 cm of it, or perhaps even try having your car go in a circle. As an example, here is some code that, when called, moves the car backward (or forward, depending on how your motors are configured) by a constant amount. Your results may vary depending on the surface on which this movement is being tested.exactly 2.5 cm.

. 
Figure 10: Example code to move the car using the picar-4wd library


These are just some example ideas that you can try to get comfortable with the library. When you feel ready, proceed to the next section to get started writing a script to make your car autonomous!

Step 4: Environment Scanning (Mapping)

As an autonomous car drives, it must be aware of its environment. You'd think it could just follow GPS, but driving is much more complex than just knowing what roads to follow. There are other cars on the road, there will be obstacles such as road construction, pedestrians will step out in front, etc. Your car needs to be aware of its microenvironment to perform operations such as crash avoidance, summon, etc. 

Luckily, the problem of automatically discovering a physical environment is one that has been long studied in the field of robotics. The field of robotic mapping has its roots in cartography and computer vision - there are a wide variety of algorithms that have been proposed, many of which typically involve a scanning process where the device "looks around" in some fashion, then internally constructs some sort of data structure representation of its environment that is amenable to processing (for later navigation and planning steps).

Real world self-driving cars use similar approaches, leveraging arrays of sensors mounted in various locations on the car, but join this information together with vast amounts of mapping data collected by GPS/fleets of other cars. This is what they use for high level navigation and routing from point A to point B. They also have object detection systems that are pre-trained to detect humans, other cars, stop signs, etc.

Since GPS is not granular enough to support true autonomy; cars make use of probabilistic SLAM (simultaneous localization and mapping) algorithms constantly being fed sensor data, they can pinpoint where they are relative to the map in real-time, and stitch together a thorough map built off pre-existing data and real-time data. SLAM algorithms aim to answer the question “what is the probability of the current map state (described by the locations of the obstacles and the agent) given the current set of sensor observations”. The process of mapping involves computing the probability of each position being occupied whereas localization involves finding the agent’s own frame of reference.  

For the purposes of this lab we'll keep things much simpler though. What you will do is write a mapping algorithm that simply keeps your car from crashing into things. Your car will act much like a Roomba - it will approach objects, but before crashing into them, back up and traverse in another direction.

What you need to do: Write a program that uses the ultrasonic sensor to detect obstacles that come within several centimeters of your car's front bumper. When your car gets within that obstacle, it should stop, choose another random direction, back up and turn, and then move forward in the new direction.

Where you place your ultrasonic sensor can make a difference, especially if you're interested in exploring more advanced mapping algorithms -- if you're having trouble getting good readings (eg you see noise in them), try to remove possible sources of interference - try putting the car on a different surface (e.g., different kind of floor), take it inside if you're outside, etc. You can also make little blinders that direct the line of vision directly forward, like this:


Figure 11: Optional "Blinders" installed on ultrasonic sensor to improve proximity readings (could use dime rolls, rolled up pieces of paper, or 3D printed materials). You don't really need to do this but you can if you want to get extra precision in your readings.

Step 5: Driving
Next, we need to figure out if your car works. One idea would be to take it out on city streets. Put that sucker down in the middle of the road in front of your house and tell it to drive to the grocery store. This would clearly not be a good idea because your car is much smaller than other cars and it would get run over and broken by them.

Hence, in this part, you will be setting up a small obstacle course indoors. Pick a room in your house and set up a pretend environment for your car. We suggest something along these lines:


Figure 12: Example environmental setup you can use to test your car.


As part of your obstacle course, we need to test out the avoidance system you developed: Is your car able to recognize objects it should avoid? Is it able to do that accurately? Are there false positives (where it sees objects that do not exist) or false negatives (where it misses objects that are there)? Is your car able to route around objects? Is it able to do so correctly, leaving sufficient clearance around them? Is it able to do so quickly enough, to avoid a crash?

For the routing, the car should go around objects that are obstructing its path. In particular, the distance sensor should be used to recognize that an obstacle is in the way, and halt your car and drive around the obstacle. For an added challenge, try moving your objects around -- routing around the dynamic objects is risky as the objects' movement is far more unpredictable than a fixed obstacle, so we use the distance sensor to act as an override for our routing.

Part 1 Submission and Grading

To submit your own work, you will create a demo video (under 5 mins). The video should be hosted privately on cloud, with access permission given to the course staff. Do not upload the video to coursera. The demo video should contain:
4 main points in the rubric.
The code you wrote as well as a walk through
 
Your final submission should be a report using this template in PDF format. The report must contain:
The link for the demo video
PCB gerber files that include motors, interrupter, grayscale module and battery. 
Your design considerations for each step of the lab
Please also include screenshots of the PCB design and the assembled car in your report

The rubric for grading that you should follow is provided here:

Demo Video (50 pts)
Is the car fully assembled? (10 pts)
The hardware connection is shown and discussed (video or report), and the components can power on (Please do a quick walkthrough of the hardware components in video or report.)
10
Things generally seem plugged in but there are clearly a few things not plugged in right or things seem incomplete
5
Can the car move by itself? (10 pts)
The motors turn the wheels, can the car move under its own power, all without human involvement
10
Movement seems substantially broken in some fashion, e.g., the car attempts to move but the movement is severely hampered, or not all four wheels are turning, or the car is unable to move in a straight line, or if movement requires manual intervention to work
6
Movement does not work at all but students show the car should be able to move by showing their code, and the code seems right
3
Can the car "see" (10 pts)
The car is clearly able to perceive its environment. It stops when it reaches an obstacle, or otherwise provides some evidence of reaction from sensing its outside world via its ultrasonic sensors. 
10
Sensing works but is significantly broken, e.g., it only works sometimes or requires manual intervention for sensing to happen.
6
Sensing does not seem to work at all, but students show the car should be able to sense its environment, by showing their code, and their code seems right.
3
Can the car "navigate"? (10 pts)
Upon encountering an obstacle, the car can navigate around the obstacle in some fashion, for example by backing up and going in a different direction (it is ok if students did something more fancy here, but in general, the car should avoid obstacles in some fashion).
10
The car is doing some form of navigation but incomplete, e.g., it crashes into objects or scrapes them, doesn't stop quickly enough
6
Navigation doesn't seem to work at all, but students show correct code and pin-point possible issues
3
Code Walkthrough (10 pts)
Students clearly show and explain the code they wrote
10
Students explain the code without showing, or show the code without explaining, or show and explain only part of the code
0-5
Report (30 pts)
PCB design (10 pts)
Gerber files with the required components in PCB design
10
PCB has missing component (-2 pts for each) or the connections are unintelligible 
0-8
Report Comprehensiveness (20 pts)
Report contains detailed information about the students' thought process, such as how they approach the problem, how they reach their final implementation, the challenges they faced, etc.
20
Report is not comprehensive enough
0-19
Submission Format (5 pts)
Report is submitted in PDF format, video is hosted privately on cloud with access permission granted and does not exceed the 5 minutes limit.
5



Category
Points
Video
50
Report
30
Submission Format
5
Total
85


Frequently Asked Questions
"Can the car move by itself?": The car can move by using the example code "keyboard_control.py". Do we need to write our own code to make the car move or just show in the video that the car can be driven by that example code?
Ans: It is ok to use that file, just clearly state you are using that code.
"Can the car see"/"can the car navigate": I see the example code "obstacle_avoidance.py" and "track_line" can implement the similar functions, but cannot work well, (for example the "obstacle_avoidance.py" can lead to avoiding the obstacle to some extend, but many times the car still crashes into the objects). I was wondering if our code work could base on the example codes and do some improvements.
Ans: It is ok to base your code on the original code, but go through every line to make sure you understand it (I suggest you write it yourself to force yourself to do that). Also state clearly what code you leverage in your writeup.
Topology: I feel for lab1 we don't need to have extra circuits, just using the default assembly (per the assembly instructions) would make it work. So the topology is just shown what it originally has would be okay?
Ans: That is fine, but please feel free to innovate and create extra circuits, we may give extra credit for that sort of thing.
Does one group only need to submit one video and report?
Ans: One group only needs to submit one video and report, up to the team to decide how to allocate the work among yourselves.
How to set the default servo angle to 0?
Ans: There's a function called set_angle(self, angle) declared in servo.py pass in 0 to see if your servo arm needs to be tuned, since the arm could be installed slightly off. If the arm is installed with an offset, you can either manually reinstall the arm (call the function so it turns to 0, then remove the arm and install it, so it faces forward) or in software just always have an offset value before passing the angle in.
Does the camera installation direction matter?
Ans: No, in software you can change the orientation of the frame, so just make the camera faces forward.
In the naive mapping part in the report, what contents should be included in this part?
Ans: Just explain the algorithm or the basic functionality that you implemented for "seeing" its environment.
When generating Gerber files, which layers do we need to select? 
Ans: Make sure you always include at least these layers: 
	F.Cu (Front Copper) 
	B.Cu (Back Copper, if used) 
	F.Mask (Front Solder Mask) 
	B.Mask (Back Solder Mask) 
	F.SilkS (Front Silkscreen – for labels) 
	Edge.Cuts (Board outline – required!) 
If you miss Edge.Cuts, your board won’t have a shape. If you miss F.Mask/B.Mask, your solder pads may not be exposed correctly. Always open your files in the Gerber Viewer before submitting to double-check.
Where to Go From Here

In this lab, you gained familiarity and comfort with doing basic IoT engineering. You learned how to work with Raspberry Pi, one of the most common platforms for IoT development. You also learned how to use sensors and actuators to interact with the environment using simple robotics.

There is certainly more to IoT than this, and I encourage you to continue your journey into the world of IoT, both in terms of gaining more extensive understanding of the concepts underlying these technologies as well as extending your breadth to other IoT technologies, which we will do in later labs (in fact, the next two labs will build upon your car to give it powerful new capabilities - we will develop networking leveraging bluetooth/wifi, as well as develop a cloud backend with machine learning). That said, the experiences you gained in this lab are general, and with them, you should now be able to attempt things like:

Create an automatic cat feeder that dispenses food whenever it sees your cat (OpenCV already has cat detection algorithms, and you can find various sorts of motors/housings on websites like adafruit.com).
Create an intelligent manufacturing safety system to turn off assembly machines when human yells are detected (look around at your workplace: many lighting/security/HVAC systems, robotics, electrical distribution systems, even the car you drive, are able to be monitored and controlled by interfaces where you simply adjust voltages on input wires).
Continuously monitor health of an ill family member or friend and leverage machine learning to find problems early (regulation slows technology adoption in healthcare - many open-source projects are leveraging increasingly cheap medical sensors to do things far beyond what hospitals can do on their own).


IOT Lab 1: IoT Devices (Part 2)
In part one of this lab you constructed a basic self-driving car. Currently your car acts kind of like a Roomba - it goes until it encounters an obstacle, then backs up and tries another path, etc. In this lab, you will give the gift of computer vision to your car. It will be able to understand what obstacles are in front of it, and much more. To do this, we will have to build a more advanced understanding of computer intelligence, which we will do through the following steps.
Step 6: More Advanced Mapping
Overview:
In the real world, intelligent systems will typically construct a formal representation of their physical environment to assist in their navigation capabilities. Self-driving cars for example will construct a "map" of the environment that consists of a scanned 3-dimensional point representation observed from various sensors on the car, annotated with semantics (e.g., "this part over here is a stop sign, this part over here is a person"). To provide more advanced navigational capabilities to our car, we will start by implementing a more advanced mapping algorithm -- to keep things simple, we'll work in two dimensions, though what you learn generalizes directly to higher dimensional analysis.

Objectives:
You will implement a more general non-probabilistic mapping model
You will emulate localization by incrementing position based on velocity readings. 

Our car must use data from the ultrasonic sensor and potentially the camera to detect obstacles around it as well as their distances. To do this, you can create a numpy array map data structure in your python code, where you store the data as a numpy array of 0’s and 1’s, where a 1 represents there is an obstacle within a certain threshold distance, and a 0 indicates there is not, and the array index indicates the angle (from the car's perspective).

One way to perform the mapping is to scan the surroundings by reading distances from the ultrasonic sensor every few degrees, and interpolating distances in between those points as well to generate a rough map of the surroundings.

For example, if you find the distance to the nearest object at 60 degrees on the servo to be 20 cm and the distance at 55 degrees to be 20 cm as well, you can consider those as two points on a coordinate grid, calculate the slope between them, and fill in all points between them that lie on that line as being “objects” in your internal map. 

Imagine a 100x100 numpy array where each element represents a 1x1 cm grid. If your car is at (0,0) and you find the distance reading on the ultrasonic sensor at 0 degrees shows 10 cm, we would mark (10, 0) as a 1, since that is where we find our first object. Variants of SLAM (Simultaneous localization and mapping) algorithms can also be used for this step.

Here (mirror-MOV) (mirror-MP4) is a quick walkthrough of an example conversion from ultrasonic readings to a numpy array.
Step 7: Object Detection
Objectives: 
You will learn how to work with computer vision using OpenCV, leveraging the Raspberry Pi and camera.
You will leverage neural networks to automate object recognition. You will be running lite CNN models, powered by TensorFlow, on a Raspberry Pi. 

Note: If you are using a different Raspberry Pi model or robot car, these instructions for object detection libraries may not work exactly as described. Please refer to the Frequently Asked Questions for more details. You may find it easier to use Vilib or MediaPipe instead. That said, we have kept the original instructions available for reference.
Your target is to perform real-time (around 1 fps) object detection via the Raspberry Pi. The Raspberry Pi 4B has a dedicated camera port for high speed video transmission. The challenge lies in the image processing task. The first thing you will certainly want to do is to install the picamera module, which is a python module for transforming video feed into numpy arrays. In the old days, you would need to build the python wheel on Raspberry Pi from scratch (which takes a lot of work), or cross compile the module against the ARM architecture used by Raspberry Pi (which is faster, but still hard to manage the dependencies). However, today you can leverage pip to install these modules with predefined build flows. Simply type pip install --user picamera[array] and you would be able to process the camera feed via numpy in real time. (Also you can try to test your camera by taking a still picture using the raspistill command in the CLI.)

We suggest you use OpenCV for image preprocessing and TensorFlow Lite’s Interpreter API for object detection. Although we use pre-trained models only for this use case, it can still be challenging to implement the object detection feature if you don’t have previous experience with TensorFlow and computer vision. So, we recommend that you read the following reference materials to understand the basics of leveraging TensorFlow in object detection applications: 

Installing Raspberry Pi Camera:
https://www.raspberrypi.com/documentation/accessories/camera.html#installing-a-raspberry-pi-camera 
Checking Raspberry Pi Camera
	Test with command: libcamera-hello
https://www.raspberrypi.com/documentation/computers/camera_software.html#introducing-the-raspberry-pi-cameras
How to set up and use Tensorflow Lite on the Raspberry Pi: 
https://www.tensorflow.org/lite/guide/python
How to set up and use OpenCV on the Raspberry Pi: 
https://qengineering.eu/install-opencv-on-raspberry-pi.html
# check for updates
$ sudo apt-get update
$ sudo apt-get upgrade
# dependencies
$ sudo apt-get install build-essential cmake git unzip pkg-config
$ sudo apt-get install libjpeg-dev libpng-dev
$ sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev
$ sudo apt-get install libgtk2.0-dev libcanberra-gtk* libgtk-3-dev
$ sudo apt-get install libgstreamer1.0-dev gstreamer1.0-gtk3
$ sudo apt-get install libgstreamer-plugins-base1.0-dev gstreamer1.0-gl
$ sudo apt-get install libxvidcore-dev libx264-dev
$ sudo apt-get install python3-dev python3-numpy python3-pip
$ sudo apt-get install libtbb2 libtbb-dev libdc1394-22-dev
$ sudo apt-get install libv4l-dev v4l-utils
$ sudo apt-get install libopenblas-dev libatlas-base-dev libblas-dev
$ sudo apt-get install liblapack-dev gfortran libhdf5-dev
$ sudo apt-get install libprotobuf-dev libgoogle-glog-dev libgflags-dev
$ sudo apt-get install protobuf-compiler
# install command
$ pip3 install opencv-contrib-python
Example code (use this code to get started, you should build off of this)please consider just repurposing this code, it will save you time): https://github.com/tensorflow/examples/blob/master/lite/examples/object_detection/raspberry_pi/README.md

As a first step, try to get a picture of a stop sign recognized. To test this, you can pull up a picture of a stop sign on your cell phone, and hold it several inches in front of your car's camera. 

Now we have the camera feed, which should be  processed via TensorFlow. However, this is still not enough. Remember that Raspberry Pi is rather constrained in its computation resources, and we need to choose a suitable CNN model for image recognition. Quantized, low precision models, which leverage 8 bit integers to replace floating point operations, are most suitable for inference in mobile devices. Luckily, they provide good performance for the Pi as well . The example above uses Coco, a basic pre-trained image recognition model, but you can try loading different models.   You may also want to train the model by yourself, if you want some more specific image recognition tasks (i.e. increased accuracy on certain objects you might encounter on a street like certain road signs, traffic cones, etc) . However, that takes a lot of GPU cycles, so most likely could not be finished on a laptop (and definitely not on a Pi).

Note: You should notice that once the application starts running, the Pi will most likely overheat due to high CPU utilization. The CPU will then decrease its frequency (and even shut down itself) for self protection, which leads to significant performance drop in your application. You may want to buy a fan on the device sheet (or simply open the window to let the cold wind in Champaign do the work, depending on the season. Just kidding.) to keep the CPU performing well. 

Equipped with the above prerequisites, you can start writing the object detection application. There are certainly a lot of methods to do it, so we’ll leave the creativity to you! Since the Pi is low in computation power, you should not expect it to be able to process the video with the standard 25FPS. Actually, the best you could get with current Python module support should be around 1 FPS. Optimizing your code to reach this level will be challenging but fun. Ultimately, we want you to derive the best practice in your report to build a real-time video processing pipeline on the Pi. In your report, answer the following questions:

Would hardware acceleration help in image processing? Have the packages mentioned above leveraged it? If not, how could you properly leverage hardware acceleration?
Would multithreading help increase (or hurt) the performance of your program?
How would you choose the trade-off between frame rate and detection accuracy?

Once you have a working Pi that you have connected the Picamera module with as well as working tensorflow code, the last step is using the ultrasonic sensor in conjunction with the chassis to scan your surroundings and map out a path to the goal. For the purposes of this lab, we can set the target to be a relative distance away from the starting point, i.e. 10 feet north and 5 feet east of the starting point. Using the picar-4wd library code, you can write wrapper functions that move the car a certain distance in a certain direction when called.
Step 8: Self-Driving Navigation (Routing)
Overview: 
When we want to drive somewhere, we simply put the address into Google Maps and let it tell us where to make turns and which roads to take. Commercial systems like Tesla’s autopiloting use similar global planning methods for general navigation, but when changing lanes or making tight turns, following such global methods won’t be very useful. Instead, the system must be able to generate a more granular map and a local plan on top of that to follow to reach the goal. An overview of the various autonomous vehicle methods being used commercially can be found here. These systems have millions, if not billions of miles of driving data to train and refine their models on, which we unfortunately do not have the luxury of.

Objectives:
Utilizing the advanced mapping from step 5, you will implement graph search algorithms to find a path from a given starting point to a goal.

Our mapping can be interpreted as a graph where each coordinate is a node and the edges represent the movements the car can make to each surrounding node. For the purposes of this lab, we can consider 4 possible moves from each node: up right left down.To find a path towards the target, variants of the A* algorithm can be run on the map we generated in the previous step. Like breadth-first-search, A* finds the shortest path between two points but it expands on fewer nodes than BFS and uses a heuristic (such as distance from the goal) to prioritize certain paths, hence using less memory and running faster. Given our 2-D map of the environment of 1’s and 0’s, each “edge” is a possible move in a certain direction, i.e. forward, left, right, back, and we seek to find the shortest list of moves that will get us to the target. More information on A* and pathfinding algorithms in general, can be found here: http://theory.stanford.edu/~amitp/GameProgramming/. 

However, note that once we find the optimal path, we can only follow it to a certain extent, as we must keep updating our map as we move, since we don’t know what is behind the obstacles that we move around otherwise. One way to do this is to build a map, run A* to find a route, and follow it for x number of steps before rebuilding the map. That way, we keep updating our knowledge about our surroundings while routing our car. While doing so, we must keep track of the ar’s position as well with respect to the target, as that will affect our routing. Variants of A* such as D* could be useful as well, and there are multiple solutions for this problem. Note that you also need this routing to work in conjunction with the tensorflow code; namely, if you detect a person in front of you, please wait until that person is gone before moving!

A good way to test your code is to give the car a target of "5 feet forward, 5 feet right", and place objects in the route it would take and see if it adjusts its path around them and gets to the correct destination. In addition, if you suddenly place a picture of a person in front of the car, it should halt until that person is gone, and continue its normal route.

Obstacle avoidance: You may have noticed that our routing algorithm doesn’t account for the space the car occupies. Although there are ways to mitigate this problem algorithmically (example), there is an even simpler workaround for the purposes of this lab. When we are building our surrounding map of obstacles, we can simply mark each obstacle with a clearance (i.e, marking a certain radius of surrounding cells as done in this link). This prevents our routing algorithm from trying to fit through gaps that are too small.

Figure 13: Examples for adding clearance to obstacles. Left: without clearance, Right: with clearance.

Step 9: Full Self-Driving
Overview:
Now that your car can detect objects and plan routes, we would like to test out the overall integration of your fully self-driving car. 

Objectives:
You will extend your obstacle course with various sorts of objects (stop signs, traffic cones, etc).
You will let the car self-drive on this extended obstacle course.

To construct an effective obstacle course, you'll need obstacles that look realistic enough to register in OpenCV. You are certainly welcome to use real ones, maybe you can get small ones from a dollhouse or something, but the simplest approach might be to print out pictures of such objects and mount them on cardboard. Here are some example graphics you can use, but you don't have to use these, feel free to get creative! Maybe you could take a picture of yourself and print yourself out and mount yourself as a little person on cardboard - is your car smart enough to drive around you?





 Figure 14: Sample graphics you can used to test: Stop sign, traffic lights, traffic cone  . You can cut these out and tape them up, maybe mount them on cardboard, to make your obstacle course.

  Figure 15: Example obstacle course setups. The boxes are the obstacles and the X is the destination goal. You can be creative with your obstacle course, it doesn’t have to be exactly the same as the ones above.
Part 2 Submission and Grading

Like part 1,  you will create a demo video (under 10 mins). The video should be hosted privately on cloud, with access permission given to the course staff. Do not upload the video to Coursera. The demo video should contain:
4 main points in the rubric.
The code you wrote as well as a walk through
 
Your final submission should be a report using this template in PDF format. Please include NetIDs of all group members. The report must contain:
The link for the demo video
Your design considerations for each steppart of the lab



Demo Video (70 pts)
Advanced Mapping: Are you able to generate a map indicating obstacles?  (10 pts)
This could be a 2D binary array indicating 1’s and 0’s for obstacle and no-obstacle, or vice versa. To get more innovative you could use OpenCV to build up a map image using the binary array - something like red pixels where an obstacle is detected, green elsewhere. 

A perfect submission should show the car and the obstacle(s), the car scanning its surroundings, and the map it generates in one continuous video.
Students show that the car is able to scan and generate a map of the surroundings with at least one obstacle present in the periphery.
10
The map isn’t correct but the students have correct code that they can explain and pin-point possible issues.
4
Object Detection (10 pts)
The car can correctly detect objects and students demonstrate some ideas that they tried so to speed up the fps.
10
The car can detect objects but identifies them incorrectly (wrong labels)
6
Nothing works but the students show what they tried and the issues they faced
1-3
Self-Driving Navigation (Routing) (20 pts)
A perfect submission should satisfy the following requirements:
The destination is clearly marked. You can use any format for the destination, such as specify the (x, y) end goal coordinate when you run your code.
There are at least 2 obstacles obstructing the car
The same recording must show the car navigating to at least 2 different destinations with different obstacle setup. This will help us verify that the routing and navigation indeed works.
Routing is done with A* or derivation of A*
The car must periodically rescan and recompute its mapping and routing as it navigates the course.
The car can correctly route to destination in both runs, while avoiding the obstacles.
20
The car can correctly route to both destination but run into obstacles occasionally 
15
Routing does not seem to work at all, but students show the car should be able to sense its environment and calculate the optimal path using A* by showing correct code, and can pin-point possible issues.
0-10
Routing is done without using A* or derivation of A*, or without rescans, or with obstacles oriented in a way that makes routing trivial.
0
Full Self-Driving: Is the car able to navigate the complete route correctly along with recognizing a sign (eg. stop sign) using the camera and performing necessary maneuvers? (20 pts)
A brief description of what a necessary maneuver means - If the car arrives at a stop sign, then the car must come to a halt. It should know that a stop sign is not an obstacle that it can maneuver around. Moreover, it is not necessary for the sign to obstruct the path of the car for it to come to a halt. Even if a stop sign is on one side of the path, the car must stop since the camera will capture the sign. This is just an example, you can have your own set of signs and traffic rules (please don’t let skipping traffic signals be one of them!) 

A perfect submission should satisfy the following requirements:
The destination is clearly marked.
Students should explain what traffic sign(s) they choose to recognize and what the correct response should be.
Full self-driving is done with at least 1 traffic sign and 1 obstacle that clearly obstructs the car
The car can correctly route to destination while avoiding at least 1 obstacle and correctly recognize and react to at least 1 traffic sign
20
The car can correctly route to destination but occasionally runs into the obstacle, or the car is slow to react to the traffic signs (perhaps due to low FPS) 
15
The car can correctly route to destination, but object detection does not work. Students demonstrate that the code is correct and should work and can pin-point possible issues.
10
Routing does not work or is implemented incorrectly (eg. did not use A*), but the car can recognize the traffic sign(s) and react correctly.
5
Code Walkthrough (10 pts)
Students clearly show and explain the code they wrote
10
Students explain the code without showing, or show the code without explaining, or show and explain only part of the code
0-5
Report (20 pts)
Report Comprehensiveness (20 pts)
Report contains detailed information about the students' thought process, such as how they approach the problem, how they reach their final implementation, the challenges they faced, etc.
20
Report is not comprehensive enough
0-19
Submission Format (5 pts)
Report is submitted in PDF format, video is hosted privately on cloud with access permission granted and does not exceed the 10 minutes limit
5



Category
Points
Video 
70
Report
20
Submission format
5
Total
95



Frequently Asked Questions

My ultrasonic sensor is not providing good readings, and/or my car keeps stuttering!
Please twist your wires, cover them with aluminum foil, and then with electrical tape.
Add blinders around the "eyes" of your ultrasonic sensor. Make sure your obstacles, the floor, and the wall are not reflective. 
Unplug the grayscale sensor, and build your car without it
Tom Pawelek FA 21 discovered a race condition in the source code. To fix it, at the top of the set_power() function, add the following lines:
self.pwm_pin.__init__(self.pwm_pin.channel) self.pwm_pin.pulse_width_percent(power)


"I believe that if you jam cables together, there might be some sort of interference in signals due to electromagnetic fields product of current traveling in different directions. Because signals are unlikely to go through an error correcting protocol, like TCP/IP for example, a single disruption might change the value of a reading. In order to prevent that, I covered each set of cables (not each individual cable) with aluminum foil, and on top, covered them with electrical tape. I was trying to simulate the cover of Ethernet cables. After that, stuttering practically disappeared and readings from things like the ultrasonic came back pretty accurate, false positives went down like 95% or so. Additionally, since I have two set of cars, I changed the cable intended for the Ultrasonic with the one intended for the photo interrupted of the second car. It is a little larger and allows more room to move the US while scanning without potentially pulling the sensor due to a short cable." -  Fauzi Gomez, FA 21


The servos/motors on my car aren't working. (thanks Christopher Fischer, Matt Williamson, Kim Westfall)
Make sure your screws aren't too tight.
Could be a power issue - make sure your batteries are fully charged; try changing power adapters.
Make sure all your wires are seated firmly (connected well). For example, check to make sure the wires to the power supply are not loose. 
Try resetting your car (e.g., "picar-4wd soft-reset")
If your servo works but poorly, consider ordering an MG90S (eg https://www.amazon.com/Replace-Helicopter-Airplane-Controls-Vehicle/dp/B09KXM5L7Z/) and see if that works better.

I have a motor that is going in the wrong direction.
Try reversing polarity on the input wires
If you use the "Speed" command/class, try taking that out. 

My components arrived but something is damaged.
Many manufacturers will ship you free replacements. Contact the manufacturer and let them know what happened. 

My SD card isn't working. I'm getting a Flash failed error or some similar sort of problem.
Try formatting your flash card again using the Raspberry Pi imager (https://www.raspberrypi.org/software/)
Also see https://forums.balena.io/t/flashing-raspberry-image-to-sd-card-always-fails/3091 or https://www.raspberrypi.org/forums/viewtopic.php?t=196472

My car keeps running out of power.
While you're developing/debugging, you can power the Raspberry Pi from the USB-C, to avoid draining your batteries.
Your batteries may have arrived damaged. Consider purchasing a more expensive version of the 18650 batteries, eg from here).

I'm getting errors like ImportError and ModuleNotFoundError
Make sure you ran the install command, eg "sudo python3 setup.py install" (and make sure you put "sudo" before that command)

I'm having trouble getting VNC working
If you have a spare monitor, and keyboard/mouse, you can connect it to your Raspberry Pi. Many TVs have HDMI interfaces too, so you could also try connecting that if you don't have a spare monitor.

Video Length
The video should not be more than 10 mins in length

I'm having trouble getting RP set up in Headless mode
I'm using:
RPI 4 Model B, 32GB SD Card, Mac OS Ventura 13.1, RPI Imager v1.7.3
For OS>Other>Full 32-bit
Gear Icon>
set hostname
Enable SSH password
set username/pass pi/raspberry (for backwards compatibility, not sure if necessary)
Configure Wireless LAN, Enter your SSID and Password
set locale settings
My previous efforts with adding the other steps regarding SSH, wpa_supplicant.conf and userconf.txt didn't let the RPI4b to boot.
I have an Apple Airport, which seems to intentionally make it difficult to find ip addresses for devices.  After some time the RPI4 showed up Airport Utility, but initially I used arp -a
Edit: Also followed these steps to make a backup image. https://blog.jaimyn.dev/the-fastest-way-to-clone-sd-card-macos/
Edit: Easier way to find ip address is to use the command ping raspberrypi.local See here for additional details. https://www.raspberrypi.com/documentation/computers/remote-access.html#remote-access

I want to run Fritzing but I have a Mac.
If you want to get the free version of it for Mac, you can go to Github and find the old version (which is free) for Mac.https://github.com/fritzing/fritzing-app/releases

When installing tflite-runtime on a Raspberry Pi, I get the error “externally-managed-environment”. What should I do?
Ans: You can resolve it by creating and using a virtual environment:
python -m venv tf-env --system-site-packages
source tf-env/bin/activate 
pip install tensorflow tflite-runtime
Make sure to activate this environment (source tf-env/bin/activate) every time you open a new terminal before running your code.
(Some students have reported that tflit_support is not handled in Python 3.11 or 3.12. If you are getting some errors, try switching to Python 3.9)
The documentation is for Picar-4wd. I have Picar-x and that’s causing issues:
Ans: While we can’t have documentation for all models, here are a few tips that past students have given to have the lab work with Picar-x:
Library issues: Use the installation instructions here. For PiCar-X, it might be easier to use vilib instead of object detection code given in this document.
Ultrasonic sensor is fixed, how do we make it turn?: Many students fixed this by rigging the ultrasonic sensor atop of the camera pan servo. A student reported: “I was able to do it pretty easily with some tooth picks and rubber bands. Just wanted to add that moving this sensor from the bottom caused my car to not turn properly. To make up for the weight lost on the bottom, I added some quarters as weights which worked well.”
Turning in place for navigation: Some prior students have reported that the car can turn in place by “making the tires turn in opposing directions”
14. I get “ModuleNotFoundError: No module named 'tflite_support.task'.”. I have tried downgrading to python 3.9 but then libcamera is not working.
Ans: Use mediapipe.tasks instead of tflite_support.task in detect.py and utils.py to get things going. as tflite_support.task has been deprecated and replaced by mediapipe. https://ai.google.dev/edge/mediapipe/solutions/guide. Here is a notebook outlining object detection using mediapipe that might help. https://colab.research.google.com/github/googlesamples/mediapipe/blob/main/examples/object_detection/python/object_detector.ipynb" 



