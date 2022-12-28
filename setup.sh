mkdir -p ~/.streamlit/
echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
backgroundColor = ‘#EFEDE8’\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
