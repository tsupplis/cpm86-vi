/*
 * STevie - ST editor for VI enthusiasts.   ...Tim Thompson...twitch!tjt...
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"
#include "save.h"

static char *last_message = NULL;

static void badcmd(void);
static void gotocmd(int clr, int fresh, int firstc);
static int writeit(char *fname);

void readcmdline(int firstc) /* either ':', '/', or '?' */
{
    int c, overflow = 0;
    char buff[100];
    char *p, *q, *cmd, *arg;

    gotocmd(1, 1, firstc);
    p = buff;
    if (firstc != ':')
        *p++ = firstc;
    /* collect the command string, handling '\b', ^U/@, and ESC */
    for (;;) {
        c = vgetc();
        if (c == '\n' || c == '\r' || c == EOF)
            break;
        if (c == '\033') {
            /* ESC cancels the command line */
            windcolorreset();
            clearlastmess();
            message("Normal Mode");
            updatescreen();
            return;
        }
        if (c == '\b' || c == '\177') {
            if (p > buff) {
                p--;
                overflow = 0;
                gotocmd(1, 0, firstc == ':' ? ':' : 0);
                for (q = buff; q < p; q++)
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
        if (c == '@' || c == '\025') { /* @ or ^U kills the line */
            p = buff;
            overflow = 0;
            gotocmd(1, 1, firstc);
            continue;
        }
        if (p >= buff + sizeof buff - 1) {
            overflow = 1;
            message("Command line full; use Backspace or Escape.");
            continue;
        }
        windputc(c);
        windrefresh();
        *p++ = c;
    }
    *p = '\0';
    windcolorreset();
    clearlastmess();
    if (overflow) {
        message("Command line too long; command cancelled!");
        return;
    }

    /* skip any initial white space */
    for (cmd = buff; isspace(*cmd); cmd++)
        ;

    /* search commands */
    c = *cmd;
    if (c == '/' || c == '?') {
        cmd++;
        if (*cmd == c) {
            /* the command was '//' or '??' */
            repsearch();
            return;
        }
        /* If there is a matching '/' or '?' at the end, toss it */
        p = strchr(cmd, '\0');
        if (*(--p) == c)
            *p = '\0';
        dosearch(c == '/' ? FORWARD : BACKWARD, cmd);
        return;
    }

    /* isolate the command and find any argument */
    for (p = cmd; *p != '\0' && !isspace(*p); p++)
        ;
    if (*p == '\0')
        arg = NULL;
    else {
        *p = '\0';
        while (*(++p) != '\0' && isspace(*p))
            ;
        arg = p;
        if (*arg == '\0')
            arg = NULL;
    }
    switch (cmd[0]) {
    case 'q':
        if (strcmp(cmd, "q!") == 0)
            getout();
        else if (strcmp(cmd, "q") == 0) {
            if (vi_changed)
                message("File not written out.  Use 'q!' to override.");
            else
                getout();
            return;
        }
        break;
    case 'w':
        if (strcmp(cmd, "w") == 0) {
            if (arg == NULL) {
                writeit(vi_file_name);
            } else
                writeit(arg);
            return;
        }
        if (strcmp(cmd, "wq") == 0) {
            if (writeit(vi_file_name))
                getout();
            return;
        }
        break;
    case 'x':
        if (strcmp(cmd, "x") == 0) {
            if (writeit(vi_file_name))
                getout();
            return;
        }
        break;
    case 'f':
        if (strcmp(cmd, "f") == 0) {
            if (arg == NULL)
                fileinfo();
            else {
                vi_file_name = strsave(arg);
                filemess("");
            }
            return;
        }
        break;
    case 'e':
        if (strcmp(cmd, "e") == 0 || strcmp(cmd, "e!") == 0) {
            if (cmd[1] != '!' && vi_changed) {
                message("File not written out.  Use 'e!' to override.");
            } else {
                if (arg != NULL)
                    vi_file_name = strsave(arg);
                /* clear mem and read file */
                vi_file_end = vi_top_char = vi_curs_char = vi_file_mem;
                UNCHANGED;
                p = nextline(vi_curs_char);
                readfile(vi_file_name, vi_file_end, 0);
                updatescreen();
            }
            return;
        }
        break;
    case '.':
        if (strcmp(cmd, ".=") == 0) {
            char messbuff[80];
            sprintf(messbuff, "line %lu   character %u", cntlines(vi_file_mem, vi_curs_char),
                    1U + vi_byte_span(vi_file_mem, vi_curs_char));
            message(messbuff);
            return;
        }
        break;
    case '$':
        if (strcmp(cmd, "$=") == 0) {
            char messbuff[8];
            sprintf(messbuff, "%lu", cntlines(vi_file_mem, vi_file_end) - 1UL);
            message(messbuff);
            return;
        }
        break;
    case 's':
        if (strcmp(cmd, "set") == 0) {
            if (arg == NULL)
                badcmd();
            else if (strcmp(arg, "oct") == 0) {
                octchars();
                updatescreen();
            } else if (strcmp(arg, "hex") == 0) {
                hexchars();
                updatescreen();
            } else if (strcmp(arg, "dec") == 0) {
                decchars();
                updatescreen();
            } else
                badcmd();
            return;
        }
        break;
    case 'v':
        if (strcmp(cmd, "v") == 0) {
            message(viversion());
            return;
        }
        break;
    case 'h':
        if (strcmp(cmd, "h") == 0 || strcmp(cmd, "help") == 0) {
            help();
            return;
        }
        break;
    }
    /* "r"/".r" share their first character with other commands above,
     * so they're checked separately rather than added as a new case. */
    if (strcmp(cmd, "r") == 0 || strcmp(cmd, ".r") == 0) {
        char *pp;
        if (arg == NULL) {
            badcmd();
            return;
        }
        /* find the beginning of the next line and */
        /* read file in there */
        pp = nextline(vi_curs_char);
        if (pp == NULL)
            pp = vi_file_end;
        if (readfile(arg, pp, 1))
            return;
        updatescreen();
        CHANGED;
        return;
    }
    /* :N  — go to line N (or last line if N exceeds the file) */
    {
        char *pp = cmd;
        unsigned long count = 0;
        while (isdigit((unsigned char)*pp)) {
            count = vi_count_digit(count, *pp - '0');
            pp++;
        }
        if (pp != cmd && *pp == '\0') {
            if (count > VI_COUNT_MAX)
                message("Command count too large; command cancelled!");
            else
                gotoline((unsigned)count);
            return;
        }
    }
    badcmd();
}

static void badcmd(void) { message("Unrecognized command"); }

static void gotocmd(int clr, int fresh, int firstc) {
    int n;

    windgoto(vi_rows - 1, 0);
    windcolor(2);
    if (clr) {
        /* clear the line */
        for (n = 0; n < (vi_columns - 1); n++)
            windputc(' ');
        windgoto(vi_rows - 1, 0);
    }
    if (firstc)
        windputc(firstc);
    if (fresh)
        windrefresh();
}

void message(char *s)
{
    char *p;

    if (last_message != NULL) {
        if (strcmp(last_message, s) == 0)
            return;
        free(last_message);
        last_message = NULL;
    }
    gotocmd(1, 1, 0);
    /* take off any trailing newline */
    if ((p = strchr(s, '\0')) != NULL && *p == '\n')
        *p = '\0';
    windstr(s);
    windcolorreset();
    /* Caching is optional: reporting an allocation failure must not recurse. */
    p = malloc((unsigned)(strlen(s) + 1));
    if (p != NULL)
        last_message = strcpy(p, s);
}

/* Forget the last message shown, so the next message() call always
 * redraws even if it repeats the previous one (e.g. two ':q' attempts
 * in a row on a dirty buffer should both show the warning). */
void clearlastmess(void) {
    if (last_message != NULL)
        free(last_message);
    last_message = NULL;
}

static int writeit(char *fname)
{
    char buff[128];
    const char *error;
    snprintf(buff, sizeof buff, "Writing %s...", fname);
    message(buff);
    error=vi_save_file(fname,vi_file_mem,vi_file_end,vi_binary);
    if(error) {
        message((char *)error);
        return 0;
    }
    snprintf(buff, sizeof buff, "\"%s\" %u characters", fname,
             vi_byte_span(vi_file_mem, vi_file_end));
    message(buff);
    UNCHANGED;
    return 1;
}

void filemess(char *s)
{
    char buff[128];
    snprintf(buff, sizeof buff, "\"%s\" %s", vi_file_name, s);
    message(buff);
}
