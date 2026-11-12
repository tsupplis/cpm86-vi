#include "editor.c"

static unsigned probe_value;
static unsigned timings[7];
static int failed_line;
#define REQUIRE(x) if (!(x)) { failed_line = __LINE__; goto finish; }

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

static void fixture(int longline)
{
    unsigned i;
    for (i = 0; i < (longline ? 8192U : 4096U); i++)
        vi_file_mem[i] = longline ? 'a' :
                        i % 64U == 63U ? '\n' : 'a' + i / 64U % 23U;
    vi_file_end = vi_file_mem + i;
    vi_top_char = vi_curs_char = vi_file_mem;
    vi_state = NORMAL;
    vi_changed = 0;
    resetundo();
}

int main(void)
{
    static char *names[] = {"load", "save", "middle_read", "beginning_edit",
                            "scroll", "longline_cursor", "search_miss"};
    static unsigned repeats[] = {1, 1, 1, 8, 2, 8, 4};
    FILE *report;
    char *spare = NULL;
    unsigned begin, i;
    int ok;

    REQUIRE(vi_yank_init());
    windinit();
    screenalloc();
    filealloc();
    REQUIRE(vi_set_filename("BASE.TXT"));
    spare = malloc(4096U);
    REQUIRE(spare != NULL);
    memset(spare, 'Z', 4096U);
    hexchars();
    vi_binary = 1;
    vi_file_end = vi_top_char = vi_curs_char = vi_file_mem;
    screenclear();

    begin = clock_ticks();
    ok = readfile("BASE.TXT", vi_file_mem, 1);
    timings[0] = clock_ticks() - begin;
    REQUIRE(ok == 0 && vi_file_end == vi_file_mem + 4096U);
    for (i = 0; i < 4096U; i++)
        REQUIRE(vi_file_mem[i] == (i % 64U == 63U ? '\n' :
                                 'a' + i / 64U % 23U));

    begin = clock_ticks();
    ok = vi_save_file("SAVED.TXT", vi_file_mem, vi_file_end, 1) == NULL;
    timings[1] = clock_ticks() - begin;
    REQUIRE(ok);

    begin = clock_ticks();
    ok = readfile("IMPORT.TXT", vi_file_mem + 2048U, 1);
    timings[2] = clock_ticks() - begin;
    REQUIRE(ok == 0 && vi_file_end == vi_file_mem + 4224U);
    for (i = 0; i < 4224U; i++)
        REQUIRE(vi_file_mem[i] == (i >= 2048U && i < 2176U ? 'X' :
                (i < 2048U ? i : i - 128U) % 64U == 63U ? '\n' :
                'a' + (i < 2048U ? i : i - 128U) / 64U % 23U));

    fixture(0);
    begin = clock_ticks();
    for (i = 0; i < repeats[3]; i++) {
        vi_curs_char = vi_file_mem;
        inschar('Z');
        vi_curs_char = vi_file_mem;
        delchar();
    }
    timings[3] = clock_ticks() - begin;
    REQUIRE(vi_file_end == vi_file_mem + 4096U && *vi_file_mem == 'a');

    fixture(0);
    updatescreen();
    vi_curs_char = vi_file_mem + (vi_rows - 2) * 64U;
    cursupdate();
    begin = clock_ticks();
    for (i = 0; i < repeats[4]; i++) {
        REQUIRE(onedown(1));
        cursupdate();
        windgoto((int)vi_curs_row, vi_curs_col);
    }
    timings[4] = clock_ticks() - begin;
    REQUIRE(vi_top_char == vi_file_mem + 128U);
    REQUIRE(vi_curs_char == vi_file_mem + 1600U && vi_curs_row == 23);

    fixture(1);
    vi_curs_char = vi_file_mem + 4095U;
    vi_top_char = vi_file_mem + 4080U;
    begin = clock_ticks();
    for (i = 0; i < repeats[5]; i++)
        cursupdate();
    timings[5] = clock_ticks() - begin;
    REQUIRE(vi_curs_vcol == 4095UL && vi_curs_col == 15);

    dosearch(FORWARD, "aaaaab");
    begin = clock_ticks();
    for (i = 0; i < repeats[6]; i++) {
        clearlastmess();
        repsearch();
    }
    timings[6] = clock_ticks() - begin;
    REQUIRE(vi_curs_char == vi_file_mem + 4095U && !vi_changed);
    for (i = 0; i < 4096U; i++)
        REQUIRE(spare[i] == 'Z');

finish:
    if (spare != NULL)
        free(spare);
    vi_key_exit();
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    if (report == NULL)
        return 1;
    fprintf(report, "VI PERF %s\n", failed_line ? "FAIL" : "PASS");
    if (failed_line)
        fprintf(report, "failed line %d\n", failed_line);
    else {
        fprintf(report, "capacity %u spare 4096\n", (unsigned)FILELENG);
        for (i = 0; i < 7; i++)
            fprintf(report, "%s ticks %u repeats %u\n", names[i], timings[i],
                    repeats[i]);
    }
    return fclose(report) != 0 || failed_line != 0;
}
