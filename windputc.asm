#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov dh, byte ptr cur_row_
	mov dl, byte ptr cur_col_
	mov bh, 0
	mov ah, 2
	int 10h

	mov al, byte ptr [bp+4]
	mov bh, 0
	mov ah, 0eh
	int 10h
	pop di
    pop si
    pop bp
    add sp, 2   ; Discards the saved SP value (replaces POP SP)
    pop bx
    pop dx
    pop cx
    pop ax
#endasm
