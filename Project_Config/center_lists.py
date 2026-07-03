import io
content = io.open('src/components/AppShell.tsx', 'r', encoding='utf-8').read()

# Replace the text-left wrapper with text-center
content = content.replace(
    'cursor-auto text-left text-sm',
    'cursor-auto text-center text-sm'
)

# Center the warning box header
content = content.replace(
    'flex items-center gap-2 text-warning',
    'flex items-center justify-center gap-2 text-warning'
)

# Center the list headers (h3)
content = content.replace(
    'border-b flex items-center gap-3',
    'border-b flex flex-col items-center justify-center gap-3 text-center'
)

# Center the list items (li)
content = content.replace(
    '<li className="flex flex-col py-2',
    '<li className="flex flex-col items-center justify-center text-center py-2'
)

io.open('src/components/AppShell.tsx', 'w', encoding='utf-8').write(content)