/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "stevie.h"
#include <ctype.h>
#include <stdio.h>
#include <string.h>

static void tabinout(int inout, unsigned num);
static void undochange(void);
static void applychange(int remove);
static void startinsert(char *initstr);
static int readmotion(void);
static unsigned change_lines, change_count;
static int change_remove, change_char;

/*
 * normal
 *
 * Execute a command in normal mode.
 */

void normal(int c)
{
    char *p, *q;
    int nchar;
    unsigned n;

    if (vi_renum > VI_COUNT_MAX) {
        /* Discard the rest of this command, not the next valid command. */
        if (c == 'd' || c == 'c' || c == 'y' || c == '<' || c == '>')
            readmotion();
        else if (c == 'r' || c == 'm' || c == '\'' || c == '`')
            vgetc();
        else if (c == ':' || c == '/' || c == '?') {
            do {
                nchar = vgetc();
            } while (nchar != '\n' && nchar != '\r' && nchar != '\033' && nchar != EOF);
        }
        message("Command count too large; command cancelled!");
        return;
    }

    switch (c) {
    case '\014':
        screenclear();
        updatescreen();
        break;
    case 04:
        /* control-d */
        if (!onedown((vi_rows - 1) / 2))
            beep();
        break;
    case 025:
        /* control-u */
        if (!oneup((vi_rows - 1) / 2))
            beep();
        break;
    case 06:
        /* control-f */
        if (!onedown(vi_rows - 1))
            beep();
        break;
    case 02:
        /* control-b */
        if (!oneup(vi_rows - 1))
            beep();
        break;
    case '\007':
        fileinfo();
        break;
    case 'G':
        gotoline(vi_renum);
        break;
    case 'm':
    case '\'':
    case '`':
        nchar = vgetc();
        if (nchar == '\033' || nchar == EOF)
            break;
        if (c == 'm')
            vi_mark_set(nchar);
        else if (vi_mark_jump(nchar, c == '\'')) {
            cursupdate();
            updatescreen();
        }
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
        if (vi_byte_span(vi_file_end, vi_file_max) <= 1U) {
            message("Can't add anything, file is too big!");
            break;
        }
        resetundo();
        opencmd();
        updatescreen();
        startinsert("o");
        vi_ninsert = 1;
        break;
    case 'O':
        /* Open a new line above the current line, enter insert mode. */
        if (vi_byte_span(vi_file_end, vi_file_max) <= 1U) {
            message("Can't add anything, file is too big!");
            break;
        }
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
        nchar = readmotion();
        n = (vi_renum == 0 ? 1 : vi_renum);
        switch (nchar) {
        case 'd':
            if (!yankline(n))
                break;
            sprintf(vi_redo_buff, "%udd", n);
            /* addtobuff(vi_redo_buff,'d','d',NULL); */
            beginline();
            resetundo();
            vi_uncurs_char = vi_curs_char;
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
            if (!delword(1))
                break;
            addtobuff(vi_redo_buff, 'd', 'w', 0, 0, 0, 0);
            vi_uncurs_char = vi_curs_char;
            updatescreen();
            break;
        case '$':
            /* d$ is identical to D */
            goto do_D;
        }
        break;
    case 'c':
        nchar = readmotion();
        switch (nchar) {
        case 'c':
            if (!yankline(1))
                break;
            resetundo();
            /* Go to the beginning of the line */
            beginline();
            /* delete everything but the newline */
            while (vi_curs_char < vi_file_end && *vi_curs_char != '\n')
                delchar();
            startinsert("cc");
            updatescreen();
            break;
        case 'w':
            if (!delword(0))
                break;
            startinsert("cw");
            updatescreen();
            break;
        case '$':
            /* c$ is identical to C */
            goto do_C;
        }
        break;
    case 'y':
        nchar = readmotion();
        switch (nchar) {
        case 'y':
            yankline(vi_renum == 0 ? 1 : vi_renum);
            break;
        default:
            beep();
        }
        break;
    case '>':
        nchar = readmotion();
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
        nchar = readmotion();
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
        if (!deleol())
            break;
        /* Clear vi_undo_buff so insert-ESC undo (path 3: Undelchars)
         * fires on 'u', not the deleted-text replay from deleol(). */
        *vi_undo_buff = '\0';
        /* After deleol(), cursor backed up one if line was non-empty.
         * Advance to append position (like 'a'). */
        if (vi_curs_char < vi_file_end && *vi_curs_char != '\n')
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
        CHANGED;
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
        for (p = vi_curs_char; p < vi_file_end && *p != '\n'; p++)
            ;
        if (p == vi_file_end || p + 1 == vi_file_end) {
            beep();
            break;
        }
        resetundo();
        vi_curs_char = p;
        vi_uncurs_char = vi_curs_char;
        delchar();
        vi_undo_buff[0] = 1;
        change_lines = change_count = 1;
        change_remove = 0;
        change_char = '\n';
        addtobuff(vi_redo_buff, 'J', 0, 0, 0, 0, 0);
        updatescreen();
        break;
    case '.':
        stuffin(vi_redo_buff);
        break;
    case 'u':
        if (change_lines != 0) {
            undochange();
        } else if (vi_unrpl_chars > 0) {
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
            if (!stuffin(vi_undo_buff))
                break;
            vi_curs_char = vi_uncurs_char;
            *vi_undo_buff = '\0';
        } else if (vi_undel_chars > 0) {
            if (vi_undel_chars > UNDO_LIMIT) {
                message("Undo too big; command rejected!");
                break;
            }
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
    case '~':
        /* Toggle case of [count] chars from cursor position */
        n = (vi_renum == 0 ? 1 : vi_renum);
        if (*vi_curs_char != '\n') {
            resetundo();
            vi_uncurs_char = vi_curs_char;
            sprintf(vi_redo_buff, "%u~", n);
            sprintf(vi_undo_buff, "%u~", n);  /* ~~ is its own inverse */
            while (n > 0 && vi_curs_char < vi_file_end && *vi_curs_char != '\n') {
                n--;
                if (islower(*vi_curs_char))
                    *vi_curs_char = toupper(*vi_curs_char);
                else if (isupper(*vi_curs_char))
                    *vi_curs_char = tolower(*vi_curs_char);
                vi_curs_char++;
            }
            /* Don't land on the newline or logical EOF. */
            if (vi_curs_char > vi_uncurs_char &&
                (vi_curs_char == vi_file_end || *vi_curs_char == '\n'))
                vi_curs_char--;
            CHANGED;
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

static void tabinout(int inout, unsigned num) {
    unsigned lines = 0, changes = 0, i;
    char *savecurs = vi_curs_char, *start, *p;

    if (vi_curs_char >= vi_file_end)
        return;
    beginline();
    start = vi_curs_char;
    vi_curs_char = savecurs;
    p = start;
    do {
        lines++;
        if (!inout || *p == '\t')
            changes++;
        p = nextline(p);
    } while (p != NULL && lines < num);
    if (changes == 0)
        return;
    if (lines > sizeof vi_undo_buff * 8U) {
        message("Indentation too big for undo; command rejected!");
        return;
    }
    if (!inout && changes >= vi_byte_span(vi_file_end, vi_file_max)) {
        message("Can't add anything, file is too big!");
        return;
    }
    resetundo();
    vi_uncurs_char = start;
    memset(vi_undo_buff, 0, (lines + 7U) / 8U);
    for (p = start, i = 0; i < lines; i++) {
        if (!inout || *p == '\t')
            vi_undo_buff[i / 8U] |= 1U << (i % 8U);
        p = nextline(p);
    }
    change_lines = lines;
    change_count = changes;
    change_remove = !inout;
    change_char = '\t';
    applychange(inout);
    sprintf(vi_redo_buff, "%u%s", num, inout ? "<<" : ">>");
    CHANGED;
}

/* One bit per visited line selects literal single-byte edits, including J. */
static void applychange(int remove)
{
    char *p = vi_uncurs_char;
    unsigned i;
    for (i = 0; i < change_lines; i++) {
        if ((unsigned char)vi_undo_buff[i / 8U] & (1U << (i % 8U))) {
            if (remove) {
                vi_marks_delete(p, 1);
                memmove(p, p + 1, vi_byte_span(p + 1, vi_file_end));
                vi_file_end--;
            } else {
                vi_marks_insert(p, 1);
                memmove(p + 1, p, vi_byte_span(p, vi_file_end));
                *p = change_char;
                vi_file_end++;
            }
        }
        p = nextline(p);
        if (p == NULL)
            p = vi_file_end;
    }
    vi_curs_char = vi_uncurs_char;
    if (change_char == '\n' && vi_curs_char > vi_file_mem)
        vi_curs_char--;
}

static void undochange(void)
{
    char *p = vi_uncurs_char;
    unsigned i;
    int dirty = vi_changed;

    if (!change_remove && change_count > vi_byte_span(vi_file_end, vi_file_max)) {
        message("Can't add anything, file is too big!");
        return;
    }
    for (i = 0; i < change_lines; i++) {
        if (p < vi_file_mem || p > vi_file_end ||
            (p == vi_file_end && (i + 1U != change_lines || change_remove)) ||
            (change_remove &&
             ((unsigned char)vi_undo_buff[i / 8U] & (1U << (i % 8U))) &&
             *p != change_char)) {
            message("Unable to undo change; command rejected!");
            return;
        }
        p = nextline(p);
        if (p == NULL)
            p = vi_file_end;
    }
    applychange(change_remove);
    change_remove = !change_remove;
    vi_changed = vi_undo_changed;
    vi_undo_changed = dirty;
    updatescreen();
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

static int readmotion(void)
{
    int c = vgetc();
    if (c == '\'' || c == '`') {
        vgetc();
        message("Mark operator motions are not supported!");
        return 0;
    }
    return c;
}

void resetundo(void) {
    vi_undo_changed = vi_changed;
    vi_undel_chars = 0;
    *vi_undo_buff = '\0';
    vi_uncurs_char = NULL;
    vi_unrpl_chars = 0;
    change_lines = 0;
}
