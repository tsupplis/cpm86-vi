codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_yseg_init_
vi_yseg_init_ proc near
    push bp
    push ds
    push es
    push bx
    push cx
    push dx
    push si
    push di
    mov bx,1000h
    mov ah,48h
    int 21h
    jnc yd2_allocated
    xor ax,ax
yd2_allocated:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop es
    pop ds
    pop bp
    ret
vi_yseg_init_ endp

    public vi_yseg_capacity_
vi_yseg_capacity_ proc near
    mov ax,42112
    ret
vi_yseg_capacity_ endp

    public vi_yseg_free_
vi_yseg_free_ proc near
    push bp
    mov bp,sp
    push ds
    push es
    push bx
    push cx
    push dx
    push si
    push di
    mov ax,[bp+4]
    mov es,ax
    mov ah,49h
    int 21h
    mov ax,0
    jc yd2_freed
    inc ax
yd2_freed:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop es
    pop ds
    pop bp
    ret
vi_yseg_free_ endp
codeseg ends
    end
