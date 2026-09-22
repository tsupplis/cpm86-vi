#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov ax, [bp+4]
	cmp ax, 0
	je windcursor_hide
	mov cx, 0607h
	jmp windcursor_done
windcursor_hide:
	mov cx, 2000h
windcursor_done:
	mov ah, 1
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
