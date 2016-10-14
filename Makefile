MODULE = owner_notification
SRC = $(MODULE).py aws.py util.py myspace.py
CFG = $(MODULE).cfg
API = $(MODULE).api
m='latest changes'

$(MODULE).zip:	$(SRC)
		zip $(MODULE).zip $(SRC)

# git remote add origin
commit:		$(MODULE).zip $(CFG) $(API)
		rm -f *~
		git add Makefile $(API) $(CFG) $(SRC) $(MODULE).zip
		git commit -m "$(m)" 
		git push -u origin master

clean:		
		rm -f $(MODULE).zip
		rm -f *~
