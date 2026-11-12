#ifndef VI_SAVE_H
#define VI_SAVE_H
/* NULL on success; otherwise a diagnostic. Existing-file failures preserve original data (possibly in a reported backup).
 * Failure never clears editor state. */
const char *vi_save_file(const char *, const char *, const char *, int);
long vi_file_length(const char *);
#endif
