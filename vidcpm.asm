; Local CP/M helpers derived from cpm86-hacking/os.asm, MIT licensed.
; Aztec small-model near-call ABI. Preserve registers except AX.
codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    extrn vi_cpm_os_identity_:near

; DOS Plus retains a hardware scrolling origin independently of BIOS cursor
; coordinates. Re-enter the current text mode through its installed INT 10h
; hook so both XIOS and the ROM reset their state. This intentionally clears
; the screen and homes the cursor. Leave graphics modes alone.
; This entry itself checks for non-Concurrent BDOS 41h.
    public vi_cpm_video_close_
vi_cpm_video_close_ proc near
    pushf
    push bp
    push ds
    push es
    push si
    push di
    push bx
    push cx
    push dx
    call vi_cpm_os_identity_
    cmp al,41h
    jne dp_crtreset_done
    test ah,5
    jnz dp_crtreset_done
    mov ah,0Fh
    int 10h
    and al,7Fh
    cmp al,3
    jbe dp_crtreset_text
    cmp al,7
    jne dp_crtreset_done
dp_crtreset_text:
    xor ah,ah
    int 10h
dp_crtreset_done:
    pop dx
    pop cx
    pop bx
    pop di
    pop si
    pop es
    pop ds
    pop bp
    xor ax,ax
    popf
    ret
vi_cpm_video_close_ endp

codeseg ends
    end
