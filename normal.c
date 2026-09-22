/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "stevie.h"
#include <ctype.h>
#include <stdio.h>

static void tabinout(int inout, int num);
static void startinsert(char *initstr);

/*
 * normal
 *
 * Execute a command in normal mode.
 */

void normal(int c)
{
    char *p, *q;
    int nchar, n;

    switch (c) {
    case '\014':
        screenclear();
        updatescreen();
        break;
    case 04:
        /* control-d */
        if (!onedown(10))
            beep();
        break;
    case 025:
        /* control-u */
        if (!oneup(10))
            beep();
        break;
    case 06:
        /* control-f */
        if (!onedown(vi_rows))
            beep();
        break;
    case 02:
        /* control-b */
        if (!oneup(vi_rows))
            beep();
        break;
    case '\007':
        fileinfo();
        break;
    case 'G':
        gotoline(vi_renum);
        break;
    case 'l':
        if (!oneright())
            beep();
        break;
    case 'h':
        if (!oneleft())
            beep();
        break;
    case 'k':
        if (!oneup(1))
            beep();
        break;
    case 'j':
        if (!onedown(1))
            beep();
        break;
    case 'b':
        /* If we're on the first character of a word, force */
        /* an initial backup. */
        if (!issepchar(*vi_curs_char) && vi_curs_char > vi_file_mem &&
            issepchar(*(vi_curs_char - 1)))
            vi_curs_char--;

        if (!issepchar(*vi_curs_char)) {
            /* If we start in the middle of a word, back */
            /* up until we hit a separator. */
            while (vi_curs_char > vi_file_mem && !issepchar(*vi_curs_char))
                vi_curs_char--;
            if (issepchar(*vi_curs_char))
                vi_curs_char++;
        } else {
            /* back up past all separators. */
            while (vi_curs_char > vi_file_mem && issepchar(*vi_curs_char))
                vi_curs_char--;
            /* back up past all non-separators. */
            while (vi_curs_char > vi_file_mem && !issepchar(*vi_curs_char)) {
                vi_curs_char--;
            }
            if (issepchar(*vi_curs_char))
                vi_curs_char++;
        }
        break;
    case 'w':
        if (issepchar(*vi_curs_char)) {
            /* If we're on a separator, we advance to */
            /* the next non-separator char. */
            while ((p = vi_curs_char + 1) < vi_file_end) {
                vi_curs_char = p;
                if (!issepchar(*vi_curs_char))
                    break;
            }
        } else {
            /* If we're in the middle of a word, we */
            /* advance to the next word-separator. */
            while ((p = vi_curs_char + 1) < vi_file_end) {
                vi_curs_char = p;
                if (issepchar(*vi_curs_char))
                    break;
            }
            /* Now go past any trailing white space */
            while (isspace(*vi_curs_char) && (vi_curs_char + 1) < vi_file_end)
                vi_curs_char++;
        }
        break;
    case '$':
        while (oneright())
            ;
        break;
    case '0':
    case '^':
        beginline();
        break;
    case 'x':
        /* Can't do it if we're on a blank line.  (Actually it */
        /* does work, but we want to match the real 'vi'...) */
        if (*vi_curs_char == '\n')
            beep();
        else {
            addtobuff(vi_redo_buff, 'x', 0, 0, 0, 0, 0);
            /* To undo it, we insert the same character back. */
            resetundo();
            addtobuff(vi_undo_buff, 'i', *vi_curs_char, '\033', 0, 0, 0);
            vi_uncurs_char = vi_curs_char;
            delchar();
            updatescreen();
        }
        break;
    case 'a':
        /* Works just like an 'i'nsert on the next character. */
        if (vi_curs_char < (vi_file_end - 1))
            vi_curs_char++;
        resetundo();
        startinsert("a");
        break;
    case 'A':
        while (oneright())
            ;
        if (vi_curs_char < (vi_file_end - 1) && *vi_curs_char != '\n')
            vi_curs_char++;
        resetundo();
        startinsert("A");
        break;
    case 'i':
        resetundo();
        startinsert("i");
        break;
    case 'I':
        beginline();
        while (isspace(*vi_curs_char) && *vi_curs_char != '\n' &&
               vi_curs_char < (vi_file_end - 1))
            vi_curs_char++;
        resetundo();
        startinsert("I");
        break;
    case 'o':
        resetundo();
        opencmd();
        updatescreen();
        startinsert("o");
        vi_ninsert = 1;
        break;
    case 'O':
        /* Open a new line above the current line, enter insert mode. */
        resetundo();
        beginline();
        inschar('\n');
        /* Back up to the new blank line we just inserted above. */
        vi_curs_char--;
        updatescreen();
        startinsert("O");
        vi_ninsert = 1;
        break;
    case 'd':
        nchar = vgetc();
        n = (vi_renum == 0 ? 1 : vi_renum);
        switch (nchar) {
        case 'd':
            sprintf(vi_redo_buff, "%ddd", n);
            /* addtobuff(vi_redo_buff,'d','d',NULL); */
            beginline();
            resetundo();
            vi_uncurs_char = vi_curs_char;
            yankline(n);
            delline(n);
            beginline();
            updatescreen();
            /* If we have backed xyzzy, then we deleted the */
            /* last line(s) in the file. */
            if (vi_curs_char < vi_uncurs_char) {
                vi_uncurs_char = vi_curs_char;
                nchar = 'p';
            } else
                nchar = 'P';
            addtobuff(vi_undo_buff, nchar, 0, 0, 0, 0, 0);
            break;
        case 'w':
            addtobuff(vi_redo_buff, 'd', 'w', 0, 0, 0, 0);
            resetundo();
            delword(1);
            vi_uncurs_char = vi_curs_char;
            updatescreen();
            break;
        case '$':
            /* d$ is identical to D */
            goto do_D;
        }
        break;
    case 'c':
        nchar = vgetc();
        switch (nchar) {
        case 'c':
            resetundo();
            /* Go to the beginning of the line */
            beginline();
            yankline(1);
            /* delete everything but the newline */
            while (*vi_curs_char != '\n')
                delchar();
            startinsert("cc");
            updatescreen();
            break;
        case 'w':
            resetundo();
            delword(0);
            startinsert("cw");
            updatescreen();
            break;
        case '$':
            /* c$ is identical to C */
            goto do_C;
        }
        break;
    case 'y':
        nchar = vgetc();
        switch (nchar) {
        case 'y':
            yankline(vi_renum == 0 ? 1 : vi_renum);
            break;
        default:
            beep();
        }
        break;
    case '>':
        nchar = vgetc();
        n = (vi_renum == 0 ? 1 : vi_renum);
        switch (nchar) {
        case '>':
            tabinout(0, n);
            updatescreen();
            break;
        default:
            beep();
        }
        break;
    case '<':
        nchar = vgetc();
        n = (vi_renum == 0 ? 1 : vi_renum);
        switch (nchar) {
        case '<':
            tabinout(1, n);
            updatescreen();
            break;
        default:
            beep();
        }
        break;
    case '?':
    case '/':
    case ':':
        readcmdline(c);
        break;
    case 'n':
        repsearch();
        break;
    case 'C':
    do_C:
        deleol();
        /* Clear vi_undo_buff so insert-ESC undo (path 3: Undelchars)
         * fires on 'u', not the deleted-text replay from deleol(). */
        *vi_undo_buff = '\0';
        /* After deleol(), cursor backed up one if line was non-empty.
         * Advance to append position (like 'a'). */
        if (*vi_curs_char != '\n')
            vi_curs_char++;
        updatescreen();
        startinsert("C");
        break;
    case 'D':
    do_D:
        deleol();
        updatescreen();
        break;
    case 'r':
        nchar = vgetc();
        resetundo();
        if (nchar == '\n' || (!vi_binary && nchar == '\r')) {
            /* Replacing a char with a newline breaks the */
            /* line in two, and is special. */
            nchar = '\n'; /* convert \r to \n */
            /* Save stuff necessary to undo it, by joining */
            vi_uncurs_char = vi_curs_char - 1;
            addtobuff(vi_undo_buff, 'J', 'i', *vi_curs_char, '\033', 0, 0);
            /* Change current character. */
            *vi_curs_char = nchar;
            /* We don't want to end up on the '\n' */
            if (vi_curs_char > vi_file_mem)
                vi_curs_char--;
            else if (vi_curs_char < vi_file_end)
                vi_curs_char++;
        } else {
            /* Replacing with a normal character */
            addtobuff(vi_undo_buff, 'r', *vi_curs_char, 0, 0, 0, 0);
            vi_uncurs_char = vi_curs_char;
            /* Change current character. */
            *vi_curs_char = nchar;
        }
        /* Save stuff necessary to redo it */
        addtobuff(vi_redo_buff, 'r', nchar, 0, 0, 0, 0);
        updatescreen();
        break;
    case 'p':
        putline(0);
        break;
    case 'P':
        putline(1);
        break;
    case 'R':
        resetundo();
        vi_uncurs_char = vi_curs_char;
        vi_unrpl_chars = 0;
        vi_state = REPLACE;
        break;
    case 'J':
        for (p = vi_curs_char; *p != '\n' && p < (vi_file_end - 1); p++)
            ;
        if (p >= (vi_file_end - 1)) {
            beep();
            break;
        }
        vi_curs_char = p;
        delchar();
        resetundo();
        vi_uncurs_char = vi_curs_char;
        addtobuff(vi_undo_buff, 'i', '\n', '\033', 0, 0, 0);
        addtobuff(vi_redo_buff, 'J', 0, 0, 0, 0, 0);
        updatescreen();
        break;
    case '.':
        stuffin(vi_redo_buff);
        break;
    case 'u':
        if (vi_unrpl_chars > 0) {
            /* Undo Replace mode: restore original characters */
            char *rp = vi_repl_buf;
            int k = vi_unrpl_chars;
            vi_curs_char = vi_uncurs_char;
            while (k-- > 0) {
                *vi_curs_char = *rp++;
                vi_curs_char++;
            }
            vi_curs_char = vi_uncurs_char;
            vi_unrpl_chars = 0;
            vi_changed = vi_undo_changed;
            updatescreen();
        } else if (vi_uncurs_char != NULL && *vi_undo_buff != '\0') {
            vi_curs_char = vi_uncurs_char;
            stuffin(vi_undo_buff);
            *vi_undo_buff = '\0';
        } else if (vi_undel_chars > 0) {
            vi_curs_char = vi_uncurs_char;
            /* construct the next vi_undo_buff and vi_redo_buff, which */
            /* will re-insert the characters we're deleting. */
            p = vi_undo_buff;
            q = vi_redo_buff;
            *p++ = *q++ = 'i';
            while (vi_undel_chars-- > 0) {
                *p++ = *q++ = *vi_curs_char;
                delchar();
            }
            /* Finish constructing vi_uncurs_buf, and vi_uncurse_char */
            /* is left unchanged. */
            *p++ = *q++ = '\033';
            *p = *q = '\0';
            /* Undelchars has been reset to 0 */
            vi_changed = vi_undo_changed;
            updatescreen();
        } else {
            beep();
        }
        break;
    case 'H':
        help();
        break;
    default:
        beep();
        break;
    }
}

/*
 * tabinout(inout,num)
 *
 * If inout==0, add a tab to the begining of the next num lines.
 * If inout==1, delete a tab from the begining of the next num lines.
 */

static void tabinout(int inout, int num) {
    int ntodo = num;
    char *savecurs, *p;

    beginline();
    savecurs = vi_curs_char;
    while (ntodo-- > 0) {
        beginline();
        if (inout == 0)
            inschar('\t');
        else {
            if (*vi_curs_char == '\t')
                delchar();
        }
        if (ntodo > 0) {
            if ((p = nextline(vi_curs_char)) != NULL)
                vi_curs_char = p;
            else
                break;
        }
    }
    /* We want to end up where we started */
    vi_curs_char = savecurs;
    updatescreen();
    /* Construct re-do and un-do stuff */
    sprintf(vi_redo_buff, "%d%s", num, inout == 0 ? ">>" : "<<");
    resetundo();
    vi_uncurs_char = savecurs;
    sprintf(vi_undo_buff, "%d%s", num, inout == 0 ? "<<" : ">>");
}

static void startinsert(char *initstr)
{
    char *p, c;

    vi_ins_start = vi_curs_char;
    vi_ninsert = 0;
    vi_ins_ptr = vi_ins_buff;
    for (p = initstr; (c = (*p++)) != '\0';)
        *vi_ins_ptr++ = c;
    vi_state = INSERT;
    updatescreen();
}

void resetundo(void) {
    vi_undo_changed = vi_changed;
    vi_undel_chars = 0;
    *vi_undo_buff = '\0';
    vi_uncurs_char = NULL;
}
