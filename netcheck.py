#!/usr/bin/env python
#
###############################################################################
#   - Netcheck -
#
#   Author: Joel Eriksson (joel.a.eriksson@gmail.com)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################

# Standard libraries
import sys, threading, time, os, json
from optparse import OptionParser
from datetime import datetime

# Custom libraries
import ping, bottle

__version__ = "1.0.0"

###############################################################################
# LOGGING
###############################################################################
class Logger:
    def __init__(self, verbose,logfile):
        self.verbose = verbose
        self.logfile = logfile
        self.is_connected = None
        try:
            self.fo = open(logfile,mode="a",buffering=1)
        except Exception:
            sys.stderr.write("Unable to open: " + logfile + "\nUse -h for options\n")
            exit(3)
            
        self.log("START")
    
    def close(self, abnormal = False):
        if(not abnormal):
            self.log("END")
        else:
            self.log("END ABNORMAL")
        self.fo.close()
        
    def connected(self, server):
        self.console("UP   ("+server+")")
        if((self.is_connected == None) or (self.is_connected == False)):
            self.log("UP")
        self.is_connected = True

    def first_choice_disconnected(self, server):
        self.console("DOWN ("+server+") - TRYING BACKUP")        
        
    def backup_disconnected(self, server):
        self.console("DOWN ("+server+")")    
        if((self.is_connected == None) or (self.is_connected == True)):
            self.log("DOWN")
        self.is_connected = False
        
    def alive(self):
        self.log("ALIVE")
    
    def console(self,message):
        if(self.verbose):
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + 
                      " " + message)
            
    def log(self, message):
        self.fo.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + 
                      " " + message + "\n")
                      
    def get_log(self):
        try:
            file = open(self.logfile,mode="r")
        except Exception:
            sys.stderr.write("Unable to open: " + logfile + "\n")
            exit(3)
        result = []
        for line in file:
            words = line.split(" ")
            element = {
                "date"  : words[0],
                "time"  : words[1],
                "event" : words[2].rstrip()
            }
            result.append(element)
        return result
            

###############################################################################
# NETWORK SUPERVISION
###############################################################################                      
class NetworkSupervision(threading.Thread):
    def __init__(self, verbose, logfile, remote, backup, timeout, interval,
                 alive_interval):
        threading.Thread.__init__(self)
        self.kill           = threading.Event()
        self.killed         = threading.Event()
        self.logger         = Logger(verbose, logfile)
        self.remote         = remote
        self.backup         = backup
        self.timeout        = timeout
        self.interval       = interval
        self.alive_interval = alive_interval
    
    def run(self):
        alive_tmo = self.alive_interval * 60
        while not self.kill.is_set():
            if(ping.do_one(self.remote,self.timeout) != None):
                self.logger.connected(self.remote)
            elif (not self.kill.is_set()):
                self.logger.first_choice_disconnected(self.remote)
                if(ping.do_one(self.backup,self.timeout) != None):
                    self.logger.connected(self.backup)
                else:
                    self.logger.backup_disconnected(self.backup)                        
            self.kill.wait(self.interval)
            alive_tmo = alive_tmo - self.interval
            if(alive_tmo <= 0):
                self.logger.alive()
                alive_tmo = self.alive_interval * 60
        
        self.killed.set()

    def stop(self, abnormal = False):
        self.kill.set()    # Order thread exit main loop
        self.killed.wait() # Wait for until thread has exited
        self.logger.close(abnormal)
        
    def get_status(self):
        return self.logger.is_connected
        
    def get_log(self):
        return self.logger.get_log()
        

###############################################################################
# WEB API
###############################################################################
class WebAPI:
    def __init__(self, host, port, network_supervision):
        self.host   = host
        self.port   = port
        self.ns     = network_supervision
        self.app    = bottle.Bottle()
            
        self.app.route('/log', method="GET", 
                       callback=self._log)     
        self.app.route('/status', method="GET", 
                       callback=self._status)                        
        self.app.route('/', method="GET", 
                       callback=self._index)   
        self.app.route('/<path:path>', method="GET", 
                       callback=self._file) 
                       
    def start(self):
        self.app.run(host=self.host, port=self.port)
        
    def _log(self):
        bottle.response.content_type = 'application/json'
        return json.dumps(self.ns.get_log())

    def _status(self):
        bottle.response.content_type = 'application/json'
        return json.dumps({'connected' : self.ns.get_status()})
        
    def _index(self):
        return bottle.static_file("index.html", 
                                  root=os.path.dirname(__file__) + "/html/")        
    def _file(self, path):
        return bottle.static_file(path, 
                                  root=os.path.dirname(__file__) + "/html/")
                                  
###############################################################################
# MAIN PROGRAM
############################################################################### 
def main():
    parser = OptionParser()
    parser.add_option("-w", "--webapi", dest="ip_address", type="string",
                      help="Enable Web API", default="")
    parser.add_option("-p", "--port", dest="port", type="int",
                      help="Web API port (default 8081)", default=8081)                       
    parser.add_option("-l", "--log", dest="logfile", type="string",
                      help="Log file", default="netcheck.log")
    parser.add_option("-r", "--remote", dest="remote", type="string",
                      help="Remote server to ping", default="www.google.com")
    parser.add_option("-b", "--backup", dest="backup", type="string",
                      help="Backup server to ping", default="www.bing.com")
    parser.add_option("-i", "--interval", dest="interval", type="float",
                      help="Ping interval in seconds", default=5) 
    parser.add_option("-t", "--timeout", dest="timeout", type="float",
                      help="Ping response timeout in seconds", default=1) 
    parser.add_option("-a", "--alive", dest="alive_interval", type="int",
                      help="Alive interval in minutes", default=240) 
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      help="Verbose mode", default=False) 
    (options, args) = parser.parse_args()
    
    network_supervision = NetworkSupervision(options.verbose, options.logfile,
                                             options.remote, options.backup,
                                             options.timeout, options.interval,
                                             options.alive_interval
                                             )
    network_supervision.start()

    print("Running NetCheck "+__version__) 
    
    # Check if WebAPI should be started or not
    if(options.ip_address != ""):
        try:
            webApi = WebAPI(options.ip_address, options.port, 
                            network_supervision)
            webApi.start()
        except Exception as e:
            network_supervision.stop(abnormal = True)
            sys.stderr.write("Exception in Web API:\n\n")
            sys.stderr.write(str(e)+"\n")
            exit(3)               
    else:
        print("Hit Ctrl-C to quit.")
        try:
             time.sleep(600)
        except KeyboardInterrupt:
            pass
    
    print("Shutting down (please wait) ...")
    
    # It will take some time until the network supervision thread exits.
    network_supervision.stop()

if __name__ == '__main__':
    main()