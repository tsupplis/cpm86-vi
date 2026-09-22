#asm
	push cx
	push dx
	push bx
	push sp
	push bp
	push si
	push di
	mov ah, 0
	int 16h
	pop di
	pop si
	pop bp
	add sp, 2
	pop bx
	pop dx
	pop cx
#endasm
