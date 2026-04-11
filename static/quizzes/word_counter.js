function count_words(max_count) {
    let textArea = document.getElementById('answer_text');
    let word_counter = document.getElementById('word_count');

    let words_array = textArea.value.split(/\s+/).filter(Boolean);
    console.log(max_count)
    if (max_count != null) {
        if (words_array.length > max_count) {

            let allowed_words = words_array.slice(0, max_count);

            textArea.value = allowed_words.join(' ') + ' ';

            word_counter.innerText = max_count;

        } else {
            word_counter.innerText = words_array.length;
        }
    }
    else{
        word_counter.innerText = words_array.length
    }
}