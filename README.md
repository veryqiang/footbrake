# FootBrake 


## Introduce
FootBrake is a gui app that tries to do below things,

- add media into Resolve, create timeline, render job...
- select a render preset and render them out
- copy the xml/aaf files in the source folder when finished 

**In as few clicks as possible**.

Perfect for those who grade on a Windows machine, and use a mac as ProRes dongle.
It remembers the input/output folders, you only need to set it up once.

Tested working with Davinci Resolve 16.1.2 and 16.2, on macOS 10.15.1.

## Install
There are some dependencies not included in the script.

1. You need python3.6+ installed, google the package.

2. With python installed, run those commands in your terminal:
        
        pip3 install pysimplegui
        pip3 install pyyaml

    If you want to run the web version also:
        
        pip3 install pysimpleguiweb
        
3. Now is the tricky part, setting up environment variables for the Resolve scripting API. 
    
    In terminal, type:
        
        vi ~/.bash_profile
        
    Mine looks like this:        
    
    ```
    # Setting PATH for Python 3.7
    # The original version is saved in .bash_profile.pysave
    PATH="/Library/Frameworks/Python.framework/Versions/3.7/bin:${PATH}"
    export PATH
    export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/"
    export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    export PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/
    ```
4. Go to */Library/Application Support/Blackmagic Design/DaVinci Resolve*, copy a script named *python_get_resolve.py*, paste into the same folder of *FootBrake.py*.

5. cd into the same folder of the script, and run:
    
        python3 ./FootBrake.py

# Web Version

The script also comes with a web version.  You don't need to remote desktop to the 'server', instead you can visit on any local network device. But it is more limited in function, because PySimpleGUIWeb is still in alpha. Feel free to try it. It has a bigger render button.
