/*
 * Scratch program used to work out the Aztec C86 #asm/#endasm rules for
 * this toolchain: how a function returns a value, and how a #asm block
 * can read/write a C variable (global, parameter, local).
 */

static int gvar = 7;
static int vv;
static int bb;
static int result;
static unsigned bpcap;
static int first, second;

setg(v)
int v;
{
	gvar = v;
}


getg()
{
#asm
	mov ax, gvar_
#endasm
}

testparam(v)
int v;
{
	vv = v;
#asm
	mov ax, vv_
#endasm
}

setfromasm()
{
#asm
	mov ax, 55
	mov vv_, ax
#endasm
	return vv;
}

bytetest(b)
int b;
{
	bb = b;
#asm
	mov al, byte ptr bb_
	mov byte ptr result_, al
#endasm
	return result;
}

/* Try direct bp-relative addressing, assuming the compiler already set up
 * a stack frame (push bp / mov bp,sp) on function entry. Near/tiny model:
 * [bp+4] would be the first pushed parameter if BP itself was pushed after
 * a 2-byte return address. A dummy local forces the compiler to actually
 * establish a bp frame (a leaf function with no locals doesn't get one). */
stackparam(v)
int v;
{
	int dummy;
#asm
	mov ax, [bp+4]
#endasm
}

/* In case the compiler doesn't establish its own frame, or uses a
 * different offset (e.g. it saves more registers before params). */
stackparam6(v)
int v;
{
#asm
	mov ax, [bp+6]
#endasm
}

/* Capture our own bp and scan nearby stack slots from C to find where
 * the parameter 'v' actually lands. */
scanstack(v)
int v;
{
	int i;
	unsigned int *p;
#asm
	mov bpcap_, bp
#endasm
	p = (unsigned int *)bpcap;
	for (i = -8; i <= 16; i += 2)
		printf("bp%+d = %u\n", i, p[i/2]);
	printf("(looking for v=%d)\n", v);
}

/* Two-argument test: confirm which of bp+4/bp+6 holds the first vs.
 * second argument (right-to-left push order assumed). */
twoargs(a,b)
int a,b;
{
	int dummy;
#asm
	mov ax, [bp+4]
	mov first_, ax
	mov ax, [bp+6]
	mov second_, ax
#endasm
	printf("a=%d b=%d bp+4=%d bp+6=%d\n", a, b, first, second);
}

main()
{
	setg(99);
	printf("g=%d\n", getg());
	printf("p=%d\n", testparam(41));
	printf("s=%d\n", setfromasm());
	printf("b=%d\n", bytetest(200));
	printf("stack4=%d\n", stackparam(77));
	printf("stack6=%d\n", stackparam6(77));
	scanstack(77);
	twoargs(11,22);
	return 0;
}
