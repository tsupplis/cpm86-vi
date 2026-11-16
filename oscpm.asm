; Local CP/M helpers derived from cpm86-hacking/os.asm, MIT licensed.
; Aztec small-model near-call ABI. Preserve registers except AX.
codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_cpm_os_identity_
vi_cpm_os_identity_ proc near
    push bp
    mov bp,sp
    push ds
    push es
    push di
    push si
    push bx
    push cx
    push dx
    mov cx,0Ch
    int 0E0h
    pop dx
    pop cx
    pop bx
    pop si
    pop di
    pop es
    pop ds
    pop bp
    ret
vi_cpm_os_identity_    endp

codeseg ends
    end
