# Robot-Catalog
This website create, display, and delete robots and their parts. It requires an user to edit each robot.

## How to run:
1. Download and install [Python3](https://www.python.org/download/releases/3.0/), [Vagrant](https://www.vagrantup.com/), and [VirtualBox](https://www.virtualbox.org/).
1. Replace vagrant default confiduration with Vagrantfile from this directory.

### Launching Vagrant Virtual Machine: 
 1. Launch the Vagrant VM inside Vagrant sub-directory in the downloaded fullstack-nanodegree-vm repository with:

    `$ vagrant up`

 2. Then Log into:

    `$ vagrant ssh`

 3. Change directory to `/vagrant`
 
 ### Setting up the website:
1. Change directory to `\Robot-Catalog`
1. Run database_setup.py in vagrant to create database:
  `python database_setup.py`
1. Run dummyData.py in vagrant to insert fake robots and profile in database (no robot countain parts):                           
    `python dummyData.py`
1. Run robotcatalog.py in vagrant to set up the website:
