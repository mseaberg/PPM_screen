#import webbrowser
import subprocess
import shlex

url = "https://confluence.slac.stanford.edu/x/DqxiKg"
#url = 'pswww.slac.stanford.edu'

#chrome_path = r"/usr/bin/google-chrome-stable"
#webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
#webbrowser.get('chrome').open(url)
cmd = f"/cds/home/opr/xcsopr/bin/google-chrome-workstation {url}"

cmd_parts = shlex.split(cmd)
subprocess.run(cmd_parts)

