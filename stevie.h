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

#define CHANGED vi_changed = 1
#define UNCHANGED vi_changed = 0

struct charinfo {
    char ch_size;
    char *ch_str;
};

extern struct charinfo chars[];

extern int vi_state;
extern int vi_rows;
extern int vi_columns;
extern char *vi_real_scr;
extern char *vi_next_scr;
extern char *vi_file_name;
extern char *vi_file_mem;
extern char *vi_file_max;
extern char *vi_file_end;
extern char *vi_top_char;
extern char *vi_bot_char;
extern char *vi_curs_char;
extern char *vi_ins_start;
extern int vi_curs_row, vi_curs_col, vi_curs_vcol;
extern int vi_renum;
extern int vi_debug;
extern int vi_changed;
extern int vi_undo_changed;
extern int vi_binary;
extern char vi_redo_buff[], vi_undo_buff[], vi_ins_buff[];
extern char *vi_uncurs_char, *vi_ins_ptr;
extern int vi_ninsert, vi_undel_chars;
extern char vi_repl_buf[];
extern int vi_unrpl_chars;


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

/* window.c */
char *viversion(void);
void windusage(void);
void windinit(void);
void windgoto(int r, int c);
void windexit(int r);
void windcursor(int on);
void windcolor(int fg);
void windcolorreset(void);
void windclear(void);
void windstr(char *s);
void windputc(int c);
void windrefresh(void);
void beep(void);
void windrefreshcursor(void);

/* help.c */
void help(void);
