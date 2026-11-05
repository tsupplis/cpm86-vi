/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

/* One (and only 1) of the following 3 defines should be uncommented. */
/* Most of the code is machine-independent.  Most of the machine- */
/* dependent stuff is in window.c */

/*#define ATARI		1	/* For the Atari 520 ST */
/*#define UNIXPC	1	/* The AT&T UNIX PC (console) */
#define TCAP 1 /* For termcap-based terminals */

#define CMDSIZE 1024
#define UNDO_LIMIT (CMDSIZE - 3)
#define VI_COUNT_MAX 65535U
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

extern unsigned char vi_char_width[256];

extern int vi_state;
extern int vi_rows;
extern int vi_columns;
extern char *vi_file_name;
extern char *vi_file_mem;
extern char *vi_file_max;
extern char *vi_file_end;
extern char *vi_top_char;
extern char *vi_bot_char;
extern char *vi_curs_char;
extern char *vi_mark;
extern char *vi_ins_start;
extern int vi_curs_col;
extern unsigned long vi_curs_row, vi_curs_vcol;
extern unsigned long vi_renum;
extern int vi_debug;
extern int vi_changed;
extern int vi_undo_changed;
extern int vi_binary;
extern char vi_redo_buff[CMDSIZE], vi_undo_buff[CMDSIZE], vi_ins_buff[CMDSIZE];
extern char *vi_uncurs_char, *vi_ins_ptr;
extern int vi_ninsert, vi_undel_chars;
extern char vi_repl_buf[CMDSIZE];
extern int vi_unrpl_chars;


/* cmdline.c */
void readcmdline(int firstc);
void message(char *s);
void clearlastmess(void);
void filemess(char *s);

/* linefunc.c */
unsigned vi_byte_span(const char *first, const char *last);
void vi_mark_adjust(char *at, unsigned length, int remove);
unsigned long vi_count_digit(unsigned long count, unsigned digit);
char *nextline(char *curr);
char *prevline(char *curr);
char *coladvance(char *p, unsigned long col);
char *strsave(char *string);
/* Current filename is NULL or owned storage; copy before releasing aliases. */
int vi_set_filename(char *name);
void dosearch(int dir, char *str);
void repsearch(void);

/* misccmds.c */
void opencmd(void);
int issepchar(int c);
unsigned long cntlines(char *pbegin, char *pend);
void fileinfo(void);
void gotoline(unsigned n);
int yankline(unsigned n);
void putline(int k);
void inschar(int c);
void insstr(char *s);
void delchar(void);
int deleol(void);
int delword(int deltrailing);
void delline(unsigned nlines);

/* normal.c */
void normal(int c);
void resetundo(void);

/* hexchars.c */
void octchars(void);
void hexchars(void);
void decchars(void);
/* Expanded bytes only; five-cell text remains valid until a mode change. */
const char *vi_char_text(unsigned char c);
int hextoint(int c);

/* main.c */
void updatescreen(void);
void screenclear(void);
int readfile(char *fname, char *fromp, int nochangename);
int stuffin(char *s);
void addtobuff(char *s, int c1, int c2, int c3, int c4, int c5, int c6);
int vgetc(void);
int vstuffed(void);
int vpeekc(void);
int anyinput(void);

/* edit.c */
int windgetc(void);
int windpeek(void);
void edit(void);
void getout(void);
void cursupdate(void);
int oneright(void);
int oneleft(void);
void beginline(void);
int oneup(unsigned n);
int onedown(unsigned n);

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
/* Runs stay within a row; control characters use windputc(). */
void windputrun(const char *text, unsigned length);
void windrefresh(void);
void beep(void);
void windrefreshcursor(void);
#if defined(__CPM86__)
int cpm_version_below(int major, int minor);
int cpm_version_31(void);
#endif

/* help.c */
void help(void);
