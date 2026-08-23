import subprocess

def open_music():
    subprocess.Popen(['open','-a','Music'])
    return {'label':'Opening Music'}
