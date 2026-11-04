#asm
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    push bp
    push es
    mov si,[bp+4]
    mov di,[bp+6]
    mov ax,40h
    mov es,ax
    mov dh,byte ptr cur_row_
    mov dl,byte ptr cur_col_
wr_next:
    or di,di
    jz wr_done
    mov al,[si]
    mov bx,si
    mov cx,1
wr_repeat:
    cmp cx,di
    jae wr_write
    inc bx
    cmp al,[bx]
    jne wr_write
    inc cx
    jmp wr_repeat
wr_write:
    mov word ptr es:[50h],dx
    mov ah,0ah
    mov bh,0
    push cx
    int 10h
    pop cx
    add si,cx
    sub di,cx
    add dl,cl
    cmp dl,byte ptr vi_columns_
    jb wr_next
    mov dl,0
    inc dh
    jmp wr_next
wr_done:
    pop es
    pop bp
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
#endasm
