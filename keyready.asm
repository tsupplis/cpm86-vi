#asm
	push cx
	push dx
	push bx
	push sp
	push bp
	push si
	push di
	mov ah, 1
	int 16h
	jz keyready_none
	mov ax, 1
	jmp keyready_done
keyready_none:
	mov ax, 0
keyready_done:
	pop di
	pop si
	pop bp
	add sp, 2
	pop bx
	pop dx
	pop cx
#endasm
