#include "editor.c"

static unsigned probe_value;
static unsigned char output[4096], reference[4096];
static unsigned before[4], after[4], sizes[4];
static unsigned cells[1920];
static unsigned positions[2][6], issues[6];

/* Original cursor formatting and character-at-a-time output. */
static void reference_goto(int row, int col)
{
#ifdef VI_TEST_VT100
    printf("\033[%d;%dH", row + 1, col + 1);
#else
    printf("\033Y%c%c", row + 32, col + 32);
#endif
}

static void reference_diff(void)
{
    int row, col, changed, gorow = -1, gocol = -1;
    char nc;
    for (row = 0; row < vi_rows - 1; row++) {
        if (!vi_screen_load(VI_SCREEN_NEXT, row, screen_line) ||
            !vi_screen_load(VI_SCREEN_REAL, row, screen_previous))
            screenerror();
        changed = 0;
        for (col = 0; col < vi_columns; col++) {
            if ((nc = screen_line[col]) != screen_previous[col]) {
                changed = 1;
                if (!(gorow == row && gocol == col))
                    reference_goto(gorow = row, gocol = col);
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

static void capture(int enable)
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
    je vt_remove
    mov ax,word ptr es:[380h]
    mov word ptr cs:vt_old,ax
    mov ax,word ptr es:[382h]
    mov word ptr cs:vt_old+2,ax
    mov word ptr es:[380h],offset vt_interrupt
    mov ax,cs
    mov word ptr es:[382h],ax
    mov ax,ds
    mov word ptr cs:vt_ds,ax
    mov word ptr cs:vt_count,0
    jmp short vt_exit
vt_remove:
    mov ax,word ptr cs:vt_old
    mov word ptr es:[380h],ax
    mov ax,word ptr cs:vt_old+2
    mov word ptr es:[382h],ax
vt_exit:
    popf
    pop es
    pop bx
    pop ax
    jmp vt_done
vt_old dw 0,0
vt_ds dw 0
vt_count dw 0
vt_interrupt:
    pushf
    cmp cx,2
    jne vt_chain
    push ax
    push di
    push es
    mov ax,word ptr cs:vt_ds
    mov es,ax
    mov di,word ptr cs:vt_count
    cmp di,4096
    jae vt_full
    mov byte ptr es:output_[di],dl
vt_full:
    inc word ptr cs:vt_count
    pop es
    pop di
    pop ax
vt_chain:
    popf
    jmp dword ptr cs:vt_old
vt_done:
#endasm
}

static unsigned captured(void)
{
#asm
    mov ax,word ptr cs:vt_count
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
    xor bh,bh
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
/* XIOS can update the CRTC without updating the BIOS cursor shadow. */
#asm
    pushf
    cli
    push ax
    push bx
    push cx
    push dx
    push es
    mov ax,40h
    mov es,ax
    mov dx,word ptr es:[63h]
    in al,dx
    mov cl,al
    mov al,0eh
    out dx,al
    inc dx
    in al,dx
    mov bh,al
    dec dx
    mov al,0fh
    out dx,al
    inc dx
    in al,dx
    mov bl,al
    mov word ptr probe_value_,bx
    dec dx
    mov al,0ch
    out dx,al
    inc dx
    in al,dx
    mov bh,al
    dec dx
    mov al,0dh
    out dx,al
    inc dx
    in al,dx
    mov bl,al
    sub word ptr probe_value_,bx
    dec dx
    mov al,cl
    out dx,al
    pop es
    pop dx
    pop cx
    pop bx
    pop ax
    popf
#endasm
    return probe_value;
}

static void frame(int mode)
{
    int row, col;
    for (row = 0; row < vi_rows - 1; row++) {
        for (col = 0; col < vi_columns; col++)
            screen_line[col] = mode == 0 ? 'b' + col % 23 :
                               mode == 1 ? 'b' + row % 23 : 'a';
        if (mode == 2 && row == 2)
            screen_line[10] = 'Z';
        if (mode == 3 && row == 2)
            memset(screen_line, 'Z', vi_columns);
        if (mode == 4 && row == 2)
            memset(screen_line + 10, ' ', vi_columns - 10);
        if (mode == 5 && row == 2) {
            screen_line[10] = '\r';
            screen_line[11] = '$';
            screen_line[12] = (char)0x80;
            screen_line[13] = (char)0xff;
            screen_line[14] = 0x7f;
        }
        if (row == 0)
            screen_line[0] = '~';
        if (!vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
            screenerror();
    }
}

static void setup(int mode)
{
    int row;
    screenclear();
    windgoto(vi_rows - 1, 0);
    windstr("STATUS GUARD");
    for (row = 0; row < vi_rows - 1; row++) {
        memset(screen_line, 'a', vi_columns);
        if (row == 0)
            screen_line[0] = '~';
        if (!vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
            screenerror();
    }
    reference_diff();
    frame(mode);
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

int main(int argc, char **argv)
{
    static int repeats[] = {2, 2, 16, 8};
    FILE *report;
    unsigned begin, length, count, value, position;
    int mode, variant, row, col, i, ok = 1;
    void (*render)(void);
    if (!vi_yank_init())
        return 1;
    windinit();
    screenalloc();
    for (mode = 0; mode < (argc > 1 ? 6 : 4); mode++) {
        length = 0;
        position = 0;
        for (variant = 0; variant < 2; variant++) {
            render = variant ? nexttoscreen : reference_diff;
            if (argc > 1)
                setup(mode);
            else {
                screenclear();
                frame(mode);
                render();
                invalidate(mode);
            }
            capture(1);
            render();
            fflush(stdout);
            capture(0);
            count = captured();
            if (!count || count > sizeof output) {
                issues[mode] |= 1;
                ok = 0;
            } else if (!variant) {
                length = count;
                memcpy(reference, output, length);
            } else if (count != length || memcmp(reference, output, length)) {
                issues[mode] |= 2;
                ok = 0;
            }
            if (argc > 1) {
                /* XIOS commits hardware cursor updates asynchronously. */
                begin = clock_ticks();
                while ((unsigned)(clock_ticks() - begin) < 2)
                    bdos(11, 0);
                positions[variant][mode] = cursor();
                if (!variant)
                    position = positions[variant][mode];
                else if (positions[variant][mode] != position) {
                    issues[mode] |= 4;
                    ok = 0;
                }
                for (row = 0; row < vi_rows; row++)
                    for (col = 0; col < vi_columns; col++) {
                        value = cell(row, col);
                        i = row * vi_columns + col;
                        if (!variant)
                            cells[i] = value;
                        else if (cells[i] != value) {
                            issues[mode] |= 8;
                            ok = 0;
                        }
                    }
            }
            if (mode >= 4)
                continue;
            sizes[mode] = length;
            begin = clock_ticks();
            if (argc == 1)
                for (i = 0; i < repeats[mode]; i++) {
                    invalidate(mode);
                    render();
                }
            value = clock_ticks() - begin;
            if (variant)
                after[mode] = value;
            else
                before[mode] = value;
        }
    }
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    if (!report)
        return 1;
    fprintf(report, "VI VT %s\n", ok ? "PASS" : "FAIL");
    for (mode = 0; mode < 4; mode++)
        fprintf(report, "%d ticks %u %u bytes %u\n",
                mode, before[mode], after[mode], sizes[mode]);
    for (mode = 0; mode < 6; mode++)
        if (issues[mode])
            fprintf(report, "case %d flags %u cursor %u %u\n", mode,
                    issues[mode], positions[0][mode], positions[1][mode]);
    return fclose(report) != 0 || !ok;
}
