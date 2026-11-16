; Aztec small-model C ABI: near calls, 16-bit stack arguments, DS:data.
; Each entry owns its BP frame; all registers except AX are preserved.
codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_bios_key_read_
vi_bios_key_read_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    xor ah,ah
    int 16h
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_key_read_ endp

    public vi_bios_key_ready_
vi_bios_key_ready_ proc near
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    mov ah,1
    int 16h
    mov ax,0
    jz kb_none
    inc ax
kb_none:
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    ret
vi_bios_key_ready_ endp

codeseg ends
    end
