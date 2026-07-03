import io
content = io.open('src/components/AppShell.tsx', 'r', encoding='utf-8').read()

# 1. Fix footer layout (put button in corner)
content = content.replace(
    '<div className=\"mx-auto max-w-7xl px-6 py-4 text-xs text-muted-foreground flex flex-col sm:flex-row items-center justify-center gap-4 relative\">',
    '<div className=\"mx-auto max-w-7xl px-6 py-4 text-xs text-muted-foreground flex flex-col sm:flex-row items-center justify-between gap-4 w-full\">'
)
content = content.replace(
    '<span className=\"sm:absolute sm:left-6\">© {new Date().getFullYear()} AI AgriVision</span>',
    '<span>© {new Date().getFullYear()} AI AgriVision</span>'
)

# 2. Fix the popup and list items alignment (text-start / items-start for native RTL/LTR)
content = content.replace(
    'cursor-auto text-center text-sm',
    'cursor-auto text-start text-sm'
)

content = content.replace(
    'flex items-center justify-center gap-2 text-warning',
    'flex items-center gap-2 text-warning'
)

content = content.replace(
    'border-b flex flex-col items-center justify-center gap-3 text-center text-base',
    'border-b flex items-center gap-3 text-start text-base'
)

content = content.replace(
    '<li className=\"flex flex-col items-center justify-center text-center py-2',
    '<li className=\"flex flex-col items-start text-start py-2'
)

io.open('src/components/AppShell.tsx', 'w', encoding='utf-8').write(content)