/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

/* One (and only 1) of the following 3 defines should be uncommented. */
/* Most of the code is machine-independent.  Most of the machine- */
/* dependent stuff is in window.c */

/*#define ATARI		1	/* For the Atari 520 ST */
/*#define UNIXPC	1	/* The AT&T UNIX PC (console) */
#define TCAP 1 /* For termcap-based terminals */

#define FILELENG 24000
#define NORMAL 0
#define CMDLINE 1
#define INSERT 2
#define APPEND 3
#define FORWARD 4
#define BACKWARD 5
#define NORMAL_ESCAPE 6
#define BRACKET_ESCAPE 7
#define REPLACE 8
#define NORMAL_11 9
#define WORDSEP " \t\n()[]{},;:'\"-="

#define CHANGED Changed = 1
#define UNCHANGED Changed = 0

struct charinfo {
    char ch_size;
    char *ch_str;
};

extern struct charinfo chars[];

extern int State;
extern int Rows;
extern int Columns;
extern char *Realscreen;
extern char *Nextscreen;
extern char *Filename;
extern char *Filemem;
extern char *Filemax;
extern char *Fileend;
extern char *Topchar;
extern char *Botchar;
extern char *Curschar;
extern char *Insstart;
extern int Cursrow, Curscol, Cursvcol;
extern int Prenum;
extern int Debug;
extern int Changed;
extern int UndoChanged;
extern int Binary;
extern char Redobuff[], Undobuff[], Insbuff[];
extern char *Uncurschar, *Insptr;
extern int Ninsert, Undelchars;
extern char Replbuf[];
extern int Unrplchars;


/* cmdline.c */
void readcmdline(int firstc);
void message(char *s);
void clearlastmess(void);
void filemess(char *s);

/* linefunc.c */
char *nextline(char *curr);
char *prevline(char *curr);
char *coladvance(char *p, int col);
char *strsave(char *string);
void dosearch(int dir, char *str);
void repsearch(void);

/* misccmds.c */
void opencmd(void);
int issepchar(int c);
int cntlines(char *pbegin, char *pend);
void fileinfo(void);
void gotoline(int n);
void yankline(int n);
void putline(int k);
void inschar(int c);
void insstr(char *s);
void delchar(void);
void deleol(void);
void delword(int deltrailing);
void delline(int nlines);
char *strchr(); /* custom impl in misccmds.c, Aztec libc has none - deferred */

/* normal.c */
void normal(int c);
void resetundo(void);

/* hexchars.c */
void octchars(void);
void hexchars(void);
void decchars(void);
int hextoint(int c);

/* main.c */
void updatescreen(void);
void screenclear(void);
int readfile(char *fname, char *fromp, int nochangename);
void stuffin(char *s);
void addtobuff(char *s, int c1, int c2, int c3, int c4, int c5, int c6);
int vgetc(void);
int vpeekc(void);
int anyinput(void);

/* edit.c */
int windgetc(void);
void edit(void);
void getout(void);
void cursupdate(void);
int oneright(void);
int oneleft(void);
void beginline(void);
int oneup(int n);
int onedown(int n);

windcursor(), windcolor(), windcolorreset();

/* help.c */
void help(void);
