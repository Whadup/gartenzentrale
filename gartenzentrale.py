import sys
import subprocess
if __name__ == '__main__':
    try:
        from gartenzentrale.gartenzentrale import main
    except Exception as error:
        print ( error )
        print("Rolling Back Update")
        with open("before_update", "r") as f:
            commit = f.read()
        subprocess.run(
            "git checkout {}".format(commit),
            shell=True,
            text=True
        )
        # Do we need to revert to a previous version?
        sys.exit(1)
    try:
        main()
    except Exception as error:
        print ( error )
        # Do we need to revert to a previous version?
        sys.exit(1)
    
