; Aztec small-model C ABI: near calls, 16-bit stack arguments, DS:data.
; Each entry owns its BP frame; all registers except AX are preserved.
codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_bios_goto_
vi_bios_goto_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    mov dh,byte ptr [bp+4]
    mov dl,byte ptr [bp+6]
    xor bh,bh
    mov ah,2
    push bp
    int 10h
    pop bp
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_goto_ endp

    public vi_bios_cursor_
vi_bios_cursor_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    mov cx,0607h
    cmp word ptr [bp+4],0
    jne vb_cursor
    mov cx,2000h
vb_cursor:
    mov ah,1
    push bp
    int 10h
    pop bp
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_cursor_ endp

    public vi_bios_clear_
vi_bios_clear_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    mov ax,0600h
    mov bh,7
    xor cx,cx
    mov dh,byte ptr [bp+4]
    mov dl,79
    push bp
    int 10h
    pop bp
    mov ax,0200h
    xor bx,bx
    xor dx,dx
    push bp
    int 10h
    pop bp
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_clear_ endp

    public vi_bios_putc_
vi_bios_putc_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    mov dh,byte ptr [bp+4]
    mov dl,byte ptr [bp+6]
    xor bh,bh
    mov ah,2
    push bp
    int 10h
    pop bp
    mov al,byte ptr [bp+8]
    xor bh,bh
    mov ah,0Eh
    push bp
    int 10h
    pop bp
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_putc_ endp

    public vi_bios_run_
vi_bios_run_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    mov si,[bp+4]
    mov di,[bp+6]
    mov dh,byte ptr [bp+8]
    mov dl,byte ptr [bp+10]
vb_next:
    or di,di
    jz vb_done
    mov al,[si]
    mov bx,si
    mov cx,1
vb_repeat:
    cmp cx,di
    jae vb_write
    inc bx
    cmp al,[bx]
    jne vb_write
    inc cx
    jmp vb_repeat
vb_write:
    ; Use the cursor API so virtualized BIOS consoles see the position too.
    push ax
    push cx
    push dx
    push bp
    mov ah,2
    xor bh,bh
    int 10h
    pop bp
    pop dx
    pop cx
    pop ax
    mov ah,0Ah
    xor bh,bh
    push cx
    push bp
    int 10h
    pop bp
    pop cx
    add si,cx
    sub di,cx
    add dl,cl
    cmp dl,byte ptr [bp+12]
    jb vb_next
    xor dl,dl
    inc dh
    jmp vb_next
vb_done:
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_run_ endp

codeseg ends
    end
