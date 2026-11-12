#include "editor.c"

static unsigned probe_value;
static unsigned positions[2][4], characters[2][4], ticks[2][4];

/* Frozen pre-run-output diff path, using the unchanged single-byte backend. */
static void reference_diff(void)
{
    char nc;
    int row, col, changed;
    int gorow = -1, gocol = -1;

    for (row = 0; row < vi_rows - 1; row++) {
        if (!vi_screen_load(VI_SCREEN_NEXT, row, screen_line) ||
            !vi_screen_load(VI_SCREEN_REAL, row, screen_previous))
            screenerror();
        changed = 0;
        for (col = 0; col < vi_columns; col++) {
            if ((nc = screen_line[col]) != screen_previous[col]) {
                changed = 1;
                if (!(gorow == row && gocol == col))
                    windgoto(gorow = row, gocol = col);
                if (nc == '~' && col == 0) {
                    windcolor(2);
                    windputc(nc);
                    windcolorreset();
                } else
                    windputc(nc);
                gocol++;
            }
        }
        if (changed && !vi_screen_store(VI_SCREEN_REAL, row, screen_line))
            screenerror();
    }
    windrefresh();
}

static void video_hook(int enable)
{
    int dummy;
#asm
    push ax
    push bx
    push es
    pushf
    cli
    xor ax,ax
    mov es,ax
    cmp word ptr [bp+4],0
    je dh_remove
    mov ax,word ptr es:[40h]
    mov word ptr cs:dh_old,ax
    mov ax,word ptr es:[42h]
    mov word ptr cs:dh_old+2,ax
    mov word ptr es:[40h],offset dh_interrupt
    mov ax,cs
    mov word ptr es:[42h],ax
    jmp short dh_exit
dh_remove:
    mov ax,word ptr cs:dh_old
    mov word ptr es:[40h],ax
    mov ax,word ptr cs:dh_old+2
    mov word ptr es:[42h],ax
dh_exit:
    popf
    pop es
    pop bx
    pop ax
    jmp dh_done
dh_old dw 0,0
dh_positions dw 0
dh_characters dw 0
dh_disrupt dw 0
dh_remaining dw 17
dh_inside dw 0
dh_interrupt:
    cmp ah,2
    jne dh_character
    inc word ptr cs:dh_positions
    jmp dword ptr cs:dh_old
dh_character:
    cmp word ptr cs:dh_inside,0
    jne dh_chain
    cmp ah,0eh
    je dh_write
    cmp ah,0ah
    jne dh_chain
    add word ptr cs:dh_characters,cx
    jmp short dh_counted
dh_write:
    inc word ptr cs:dh_characters
dh_counted:
    inc word ptr cs:dh_inside
    pushf
    call dword ptr cs:dh_old
    dec word ptr cs:dh_inside
    push ax
    push bx
    push dx
    cmp word ptr cs:dh_disrupt,0
    je dh_return
    dec word ptr cs:dh_remaining
    jne dh_return
    mov word ptr cs:dh_remaining,17
    mov dx,1840h
    mov bh,0
    mov ah,2
    pushf
    call dword ptr cs:dh_old
dh_return:
    pop dx
    pop bx
    pop ax
    iret
dh_chain:
    jmp dword ptr cs:dh_old
dh_done:
#endasm
}

static void reset_counts(int disrupt)
{
    int dummy;
#asm
    mov word ptr cs:dh_positions,0
    mov word ptr cs:dh_characters,0
    mov word ptr cs:dh_remaining,17
    mov ax,[bp+4]
    mov word ptr cs:dh_disrupt,ax
#endasm
}

static unsigned position_count(void)
{
#asm
    mov ax,word ptr cs:dh_positions
    mov word ptr probe_value_,ax
#endasm
    return probe_value;
}

static unsigned character_count(void)
{
#asm
    mov ax,word ptr cs:dh_characters
    mov word ptr probe_value_,ax
#endasm
    return probe_value;
}

static unsigned clock_ticks(void)
{
#asm
    push es
    mov ax,40h
    mov es,ax
    mov ax,word ptr es:[6ch]
    mov word ptr probe_value_,ax
    pop es
#endasm
    return probe_value;
}

static unsigned cell(int row, int col)
{
    int dummy;
#asm
    push bx
    push cx
    push dx
    mov dh,byte ptr [bp+4]
    mov dl,byte ptr [bp+6]
    mov bh,0
    mov ah,2
    int 10h
    mov ah,8
    int 10h
    mov word ptr probe_value_,ax
    pop dx
    pop cx
    pop bx
#endasm
    return probe_value;
}

static unsigned cursor(void)
{
#asm
    push bx
    push cx
    push dx
    mov bh,0
    mov ah,3
    int 10h
    mov word ptr probe_value_,dx
    pop dx
    pop cx
    pop bx
#endasm
    return probe_value;
}

static void stripe(void)
{
    windgoto(1, 0);
#asm
    push ax
    push bx
    push cx
    mov ax,0920h
    mov bx,001eh
    mov cx,80
    int 10h
    pop cx
    pop bx
    pop ax
#endasm
}

static void frame(int mode, int iteration)
{
    int row, col;
    for (row = 0; row < vi_rows - 1; row++) {
        for (col = 0; col < vi_columns; col++) {
            if (mode == 0)
                screen_line[col] = 'a' + (col + iteration) % 23;
            else if (mode == 1)
                screen_line[col] = 'a' + (row + iteration) % 23;
            else
                screen_line[col] = 'a';
        }
        if (mode == 2 && row == 2)
            screen_line[10] = iteration % 2 ? 'X' : 'Y';
        if (mode == 3 && row == 2)
            memset(screen_line, iteration % 2 ? 'X' : 'Y', vi_columns);
        if (row == 0)
            screen_line[0] = '~';
        if (!vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
            screenerror();
    }
}

static void setup(int mode)
{
    int i;
    screenclear();
    stripe();
    windgoto(vi_rows - 1, 0);
    for (i = 0; i < vi_columns - 1; i++)
        windputc('S');
    frame(mode, 0);
    reference_diff();
}

static int physical_frame(int mode)
{
    int row, col;
    unsigned expected_cursor = mode < 2 ? (vi_rows - 1) << 8 :
                               mode == 2 ? 0x020b : 0x0300;
    if (cursor() != expected_cursor)
        return 0;
    for (row = 0; row < vi_rows - 1; row++) {
        if (!vi_screen_load(VI_SCREEN_NEXT, row, screen_line))
            return 0;
        for (col = 0; col < vi_columns; col++)
            if (cell(row, col) != ((row == 1 ? 0x1e00U : 0x0700U) |
                                   (unsigned char)screen_line[col]))
                return 0;
    }
    for (col = 0; col < vi_columns - 1; col++)
        if (cell(vi_rows - 1, col) != (0x0700U | 'S'))
            return 0;
    return 1;
}

static void invalidate(int mode)
{
    int row;
    for (row = 0; row < vi_rows - 1; row++) {
        if (mode >= 2 && row != 2)
            continue;
        if (!vi_screen_load(VI_SCREEN_REAL, row, screen_line))
            screenerror();
        if (mode == 2)
            screen_line[10] = '?';
        else
            memset(screen_line, '?', vi_columns);
        if (!vi_screen_store(VI_SCREEN_REAL, row, screen_line))
            screenerror();
    }
}

/* Batching must not turn a legacy teletype control into a printed glyph. */
static int control_frame(void (*render)(void))
{
    setup(3);
    if (!vi_screen_load(VI_SCREEN_NEXT, 2, screen_line))
        return 0;
    screen_line[10] = '\r';
    screen_line[11] = 'Z';
    if (!vi_screen_store(VI_SCREEN_NEXT, 2, screen_line))
        return 0;
    render();
    return cell(2, 10) == (0x0700U | 'Y') &&
           cell(2, 11) == (0x0700U | 'Z');
}

int main(int argc, char **argv)
{
    static int repeats[] = {4, 4, 32, 16};
    FILE *report;
    unsigned begin;
    int mode, variant, i, ok = 1;
    void (*render)(void);

    if (!vi_yank_init())
        return 1;
    windinit();
    screenalloc();
    for (mode = 0; mode < 4; mode++) {
        for (variant = 0; variant < 2; variant++) {
            render = variant ? nexttoscreen : reference_diff;
            setup(mode);
            video_hook(1);
            reset_counts(0);
            frame(mode, 1);
            render();
            positions[variant][mode] = position_count();
            characters[variant][mode] = character_count();
            reset_counts(1);
            frame(mode, 2);
            render();
            video_hook(0);
            if (!physical_frame(mode))
                ok = 0;
            setup(mode);
            frame(mode, 1);
            render();
            ticks[variant][mode] = 0;
            if (argc > 1)
                continue;
            begin = clock_ticks();
            for (i = 1; i <= repeats[mode]; i++) {
                invalidate(mode);
                render();
            }
            ticks[variant][mode] = clock_ticks() - begin;
            if (!physical_frame(mode))
                ok = 0;
        }
        if (characters[0][mode] != characters[1][mode])
            ok = 0;
    }
    if (positions[1][0] >= positions[0][0] ||
        positions[1][3] >= positions[0][3])
        ok = 0;
    if (!control_frame(reference_diff) || !control_frame(nexttoscreen))
        ok = 0;
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    if (!report)
        return 1;
    fprintf(report, "VI DISPLAY %s\n", ok ? "PASS" : "FAIL");
    for (mode = 0; mode < 4; mode++)
        fprintf(report, "%d ticks %u %u cursor %u %u chars %u %u\n", mode,
                ticks[0][mode], ticks[1][mode],
                positions[0][mode], positions[1][mode],
                characters[0][mode], characters[1][mode]);
    return fclose(report) != 0 || !ok;
}
