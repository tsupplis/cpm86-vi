#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov ax, 0600h
	mov bh, 7
	mov cx, 0
	mov dh, byte ptr clearbottom_
	mov dl, 79
	int 10h
	mov ax, 0200h
	mov bh, 0
	mov dx, 0
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
