#include <string.h>
#include "stevie.h"

#define MARK_UNSET (~0U)

static unsigned positions[26] = {
    MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET,
    MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET,
    MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET,
    MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET, MARK_UNSET,
    MARK_UNSET, MARK_UNSET
};
static int any_marks;

static int mark_index(int name)
{
    if (name >= 'a' && name <= 'z')
        return name - 'a';
    message("Mark name must be a-z!");
    return -1;
}

void vi_marks_clear(void)
{
    memset(positions, 0xff, sizeof positions);
    any_marks = 0;
}

int vi_mark_set(int name)
{
    int i = mark_index(name);
    if (i < 0)
        return 0;
    if (vi_curs_char < vi_file_mem || vi_curs_char >= vi_file_end) {
        message("No character to mark!");
        return 0;
    }
    positions[i] = vi_byte_span(vi_file_mem, vi_curs_char);
    any_marks = 1;
    return 1;
}

int vi_mark_jump(int name, int linewise)
{
    char *p;
    int i = mark_index(name);
    if (i < 0)
        return 0;
    if (positions[i] == MARK_UNSET ||
        positions[i] >= vi_byte_span(vi_file_mem, vi_file_end)) {
        positions[i] = MARK_UNSET;
        message("Mark is not set!");
        return 0;
    }
    p = vi_file_mem + positions[i];
    if (linewise) {
        while (p > vi_file_mem && p[-1] != '\n')
            p--;
        while (p < vi_file_end && (*p == ' ' || *p == '\t'))
            p++;
        if (p == vi_file_end)
            p--;
    }
    vi_curs_char = p;
    return 1;
}

/* Notify only committed edits; positions track original characters. */
void vi_marks_insert(char *at, unsigned length)
{
    unsigned i, offset;
    if (!any_marks || length == 0)
        return;
    offset = vi_byte_span(vi_file_mem, at);
    for (i = 0; i < 26; i++)
        if (positions[i] != MARK_UNSET && positions[i] >= offset)
            positions[i] += length;
}

void vi_marks_delete(char *at, unsigned length)
{
    unsigned i, offset, end;
    if (!any_marks || length == 0)
        return;
    offset = vi_byte_span(vi_file_mem, at);
    end = offset + length;
    for (i = 0; i < 26; i++) {
        if (positions[i] == MARK_UNSET || positions[i] < offset)
            continue;
        if (positions[i] < end)
            positions[i] = MARK_UNSET;
        else
            positions[i] -= length;
    }
}
