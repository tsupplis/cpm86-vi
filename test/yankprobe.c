#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "yankmem.h"

static int failures;
static char chunk[257];

static void check(int ok)
{
    if (!ok)
        failures++;
}

static unsigned char pattern(unsigned i)
{
    return (unsigned char)((i * 13U + i / 251U) & 255U);
}

static void screens(int write)
{
    unsigned image, row, i;
    for (image = 0; image <= VI_SCREEN_NEXT; image++) {
        for (row = 0; row < VI_SCREEN_MAX_ROWS; row++) {
            if (write) {
                memset(chunk, 'A' + image + row, VI_SCREEN_MAX_COLUMNS);
                check(vi_screen_store(image, row, chunk));
            } else {
                chunk[VI_SCREEN_MAX_COLUMNS] = 77;
                check(vi_screen_load(image, row, chunk));
                check(chunk[VI_SCREEN_MAX_COLUMNS] == 77);
                for (i = 0; i < VI_SCREEN_MAX_COLUMNS; i++)
                    check(chunk[i] == 'A' + image + row);
            }
        }
    }
}

int main(int argc, char **argv)
{
    char *source;
    unsigned i, offset, count, capacity;
    FILE *f;
    int initialized = vi_yank_init();

    if (argc > 1 && !strcmp(argv[1], "REJECT")) {
        if (initialized) {
            vi_yank_close();
            return 1;
        }
        puts("VI YANK INIT REJECTED");
        return 0;
    }
    if (!initialized) {
        puts("VI YANK INIT FAILED");
        return 1;
    }
    check(vi_yank_init());
    capacity = vi_yank_capacity();
    check(capacity == 24000U || capacity == VI_YANK_CAPACITY);
    printf("VI YANK CAPACITY: %u\n", capacity);
    source = malloc(capacity);
    if (source == NULL) {
        vi_yank_close();
        puts("VI YANK NEAR ALLOCATION FAILED");
        return 1;
    }
    for (i = 0; i < capacity; i++)
        source[i] = pattern(i);
    check(vi_yank_store(source, capacity));
    check(!vi_screen_load(VI_SCREEN_REAL, 0, chunk));
    check(!vi_screen_configure(0, VI_SCREEN_MAX_COLUMNS));
    check(!vi_screen_configure(VI_SCREEN_MAX_ROWS + 1, VI_SCREEN_MAX_COLUMNS));
    check(!vi_screen_configure(VI_SCREEN_MAX_ROWS, VI_SCREEN_MAX_COLUMNS + 1));
    check(!vi_screen_configure(VI_SCREEN_MAX_ROWS, 0));
    check(vi_screen_configure(VI_SCREEN_MAX_ROWS, VI_SCREEN_MAX_COLUMNS));
    screens(1);
    screens(0);
    check(!vi_screen_store(2, 0, chunk));
    check(!vi_screen_load(2, 0, chunk));
    check(!vi_screen_store(VI_SCREEN_REAL, VI_SCREEN_MAX_ROWS, chunk));
    check(!vi_screen_load(VI_SCREEN_REAL, VI_SCREEN_MAX_ROWS, chunk));
    check(!vi_screen_store(VI_SCREEN_REAL, 0, NULL));
    check(!vi_screen_load(VI_SCREEN_REAL, 0, NULL));
    memset(source, 0, capacity);
    for (offset = 0; offset < capacity; offset += count) {
        count = capacity - offset;
        if (count > 256)
            count = 256;
        chunk[256] = 77;
        check(vi_yank_load(offset, chunk, count));
        check(chunk[256] == 77);
        for (i = 0; i < count; i++)
            check((unsigned char)chunk[i] == pattern(offset + i));
    }
    for (i = 0; i < capacity; i++)
        check(source[i] == 0);
    check(!vi_yank_store(source, capacity + 1U));
    check(!vi_yank_store(NULL, 1));
    check(!vi_yank_load(capacity, chunk, 1));
    check(vi_yank_load(capacity - 1U, chunk, 1));
    check((unsigned char)chunk[0] == pattern(capacity - 1U));
    check(vi_yank_store(NULL, 0));
    check(vi_yank_load(0, NULL, 0));
    check(!vi_yank_load(0, chunk, 1));
    screens(0);
    free(source);
    vi_yank_close();
    vi_yank_close();
    check(!vi_yank_store(chunk, 1));
    check(vi_yank_capacity() == 0);
    check(!vi_screen_configure(25, 80));
    check(vi_yank_init());
    check(!vi_screen_load(VI_SCREEN_REAL, 0, chunk));
    check(vi_yank_store("again", 5));
    check(vi_yank_load(0, chunk, 5) && !memcmp(chunk, "again", 5));
    vi_yank_close();
    printf("VI YANK PASS: %d failures\n", failures);
    f = fopen("RESULT.TXT", "w");
    if (f == NULL)
        return 1;
    fprintf(f, "VI YANK PASS: %d failures\n", failures);
    if (fclose(f))
        return 1;
    return failures != 0;
}
