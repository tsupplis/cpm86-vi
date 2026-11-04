codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_yseg_write_
vi_yseg_write_ proc near
    push bp
    mov bp,sp
    pushf
    push ds
    push es
    push si
    push di
    push cx
    mov ax,[bp+4]
    mov es,ax
    mov di,[bp+6]
    mov si,[bp+8]
    mov cx,[bp+10]
    cld
    rep movsb
    pop cx
    pop di
    pop si
    pop es
    pop ds
    popf
    pop bp
    ret
vi_yseg_write_ endp

    public vi_yseg_read_
vi_yseg_read_ proc near
    push bp
    mov bp,sp
    pushf
    push ds
    push es
    push si
    push di
    push cx
    mov ax,ds
    mov es,ax
    mov ax,[bp+4]
    mov ds,ax
    mov si,[bp+6]
    mov di,[bp+8]
    mov cx,[bp+10]
    cld
    rep movsb
    pop cx
    pop di
    pop si
    pop es
    pop ds
    popf
    pop bp
    ret
vi_yseg_read_ endp
codeseg ends
    end
