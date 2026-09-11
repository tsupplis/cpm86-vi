/*
 * STevie - ST editor for VI enthusiasts.   ...Tim Thompson...twitch!tjt...
 */

#include "stdio.h"
#include "ctype.h"
#include "stevie.h"

static char *lastmess = NULL;

readcmdline(firstc)
int firstc;	/* either ':', '/', or '?' */
{
	int c;
	char buff[100];
	char *p, *q, *cmd, *arg;

	gotocmd(1,1,firstc);
	p = buff;
	if ( firstc != ':' )
		*p++ = firstc;
	/* collect the command string, handling '\b', ^U/@, and ESC */
	for ( ; ; ) {
		c = vgetc();
		if ( c=='\n'||c=='\r'||c==EOF )
			break;
		if ( c=='\033' ) {
			/* ESC cancels the command line */
			windcolorreset();
			clearlastmess();
			message("Normal Mode");
			updatescreen();
			return;
		}
		if ( c=='\b' || c=='\177' ) {
			if ( p > buff ) {
				p--;
				gotocmd(1,0,firstc==':'?':':0);
				for ( q=buff; q<p; q++ )
					windputc(*q);
				windrefresh();
			} else {
				/* Backspace on empty line cancels */
				windcolorreset();
				clearlastmess();
				message("Normal Mode");
				updatescreen();
				return;
			}
			continue;
		}
		if ( c=='@' || c=='\025' ) {	/* @ or ^U kills the line */
			p = buff;
			gotocmd(1,1,firstc);
			continue;
		}
		windputc(c);
		windrefresh();
		*p++ = c;
	}
	*p = '\0';
	windcolorreset();
	clearlastmess();

	/* skip any initial white space */
	for ( cmd = buff; isspace(*cmd); cmd++ )
		;

	/* search commands */
	c = *cmd;
	if ( c == '/' || c == '?' ) {
		cmd++;
		if ( *cmd == c ) {
			/* the command was '//' or '??' */
			repsearch();
			return;
		}
		/* If there is a matching '/' or '?' at the end, toss it */
		p = strchr(cmd,'\0');
		if ( *(--p) == c )
			*p = '\0';
		dosearch(c=='/'?FORWARD:BACKWARD,cmd);
		return;
	}

	/* isolate the command and find any argument */
	for ( p=cmd; *p!='\0' && ! isspace(*p); p++ )
		;
	if ( *p == '\0' )
		arg = NULL;
	else {
		*p = '\0';
		while ( *(++p) != '\0' && isspace(*p) )
			;
		arg = p;
		if ( *arg == '\0' )
			arg = NULL;
	}
	if ( strcmp(cmd,"q!")==0 )
		getout();
	if ( strcmp(cmd,"q")==0 ) {
		if ( Changed )
			message("File not written out.  Use 'q!' to override.");
		else
			getout();
		return;
	}
	if ( strcmp(cmd,"w")==0 ) {
		if ( arg == NULL ) {
			writeit(Filename);
			UNCHANGED;
		}
		else
			writeit(arg);
		return;
	}
	if ( strcmp(cmd,"x")==0 ) {
		if ( writeit(Filename) )
			getout();
		return;
	}
	if ( strcmp(cmd,"wq")==0 ) {
		if ( writeit(Filename) )
			getout();
		return;
	}
	if ( strcmp(cmd,"f")==0 && arg==NULL ) {
		fileinfo();
		return;
	}
	if ( strcmp(cmd,"e") == 0 || strcmp(cmd,"e!") == 0 ) {
		if ( cmd[1]!='!' && Changed ) {
			message("File not written out.  Use 'e!' to override.");
		}
		else {
			if ( arg != NULL )
				Filename = strsave(arg);
			/* clear mem and read file */
			Fileend = Topchar = Curschar = Filemem;
			UNCHANGED;
			p = nextline(Curschar);
			readfile(Filename,Fileend,0);
			updatescreen();
		}
		return;
	}
	if ( strcmp(cmd,"f") == 0 ) {
		Filename = strsave(arg);
		filemess("");
		return;
	}
	if ( strcmp(cmd,"r") == 0 || strcmp(cmd,".r") == 0 ) {
		char *pp;
		if ( arg == NULL ) {
			badcmd();
			return;
		}
		/* find the beginning of the next line and */
		/* read file in there */
		pp = nextline(Curschar);
		readfile(arg,pp,1);
		updatescreen();
		CHANGED;
		return;
	}
	if ( strcmp(cmd,".=")==0 ) {
		char messbuff[80];
		sprintf(messbuff,"line %d   character %d",
			cntlines(Filemem,Curschar),
			1+(int)(Curschar-Filemem));
		message(messbuff);
		return;
	}
	if ( strcmp(cmd,"$=")==0 ) {
		char messbuff[8];
		sprintf(messbuff,"%d",
			cntlines(Filemem,Fileend)-1);
		message(messbuff);
		return;
	}
	if ( strcmp(cmd,"set")==0 ) {
		if ( arg == NULL )
			badcmd();
		else if ( strcmp(arg,"oct")==0 ) {
			octchars();
			updatescreen();
		}
		else if ( strcmp(arg,"hex")==0 ) {
			hexchars();
			updatescreen();
		}
		else if ( strcmp(arg,"dec")==0 ) {
			decchars();
			updatescreen();
		}
		else
			badcmd();
		return;
	}
	if ( strcmp(cmd,"v")==0 ) {
		message(viversion());
		return;
	}
	if ( strcmp(cmd,"h")==0 || strcmp(cmd,"help")==0 ) {
		help();
		return;
	}
	/* :N  — go to line N (or last line if N exceeds the file) */
	{
		char *pp = cmd;
		while ( isdigit(*pp) )
			pp++;
		if ( pp != cmd && *pp == '\0' ) {
			gotoline(atoi(cmd));
			return;
		}
	}
	badcmd();
}

badcmd()
{
	message("Unrecognized command");
}

gotocmd(clr,fresh,firstc)
{
	int n;

	windgoto(Rows-1,0);
	windcolor(2);
	if ( clr ) {
		/* clear the line */
		for ( n=0; n<(Columns-1); n++ )
			windputc(' ');
		windgoto(Rows-1,0);
	}
	if ( firstc )
		windputc(firstc);
	if ( fresh )
		windrefresh();
}

message(s)
char *s;
{
	char *p;

	if ( lastmess!=NULL ) {
		if ( strcmp(lastmess,s)==0 )
			return;
		free(lastmess);
	}
	gotocmd(1,1,0);
	/* take off any trailing newline */
	if ( (p=strchr(s,'\0'))!=NULL && *p=='\n' )
		*p = '\0';
	windstr(s);
	windcolorreset();
	lastmess = strsave(s);
}

/* Forget the last message shown, so the next message() call always
 * redraws even if it repeats the previous one (e.g. two ':q' attempts
 * in a row on a dirty buffer should both show the warning). */
clearlastmess()
{
	if ( lastmess != NULL )
		free(lastmess);
	lastmess = NULL;
}

writeit(fname)
char *fname;
{
	FILE *f;
	char buff[128];
	char *p;
	int n;

	sprintf(buff,"Writing %s...",fname);
	message(buff);

 	if ( (f=fopen(fname,"w")) == NULL ) {
		message("Unable to open file!");
		return(0);
	}

	for ( n=0,p=Filemem; p<Fileend; p++,n++ ) {
		if ( !Binary && *p == '\n' )
			putc('\r',f);
		putc(*p,f);
	}
	if ( !Binary )
		putc(0x1A,f);
	sprintf(buff,"\"%s\" %d characters",fname,n);
	fclose(f);

	message(buff);
	UNCHANGED;
	return(1);
}

filemess(s)
char *s;
{
	char buff[128];
	sprintf(buff,"\"%s\" %s",Filename,s);
	message(buff);
}
