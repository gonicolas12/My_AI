"""
Modèle seq2seq local basé sur T5 (HuggingFace Transformers, 100% offline après le premier download).
"""
import os
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

from transformers import BartForConditionalGeneration, BartTokenizer

class Seq2SeqModel:
    def __init__(self, model_name_or_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Chemin local par défaut (toujours offline)
        local_path = os.path.join(os.path.dirname(__file__), "bart-base-local")
        if model_name_or_path is None:
            model_name_or_path = local_path
        if not os.path.isdir(model_name_or_path):
            raise FileNotFoundError(f"Le dossier du modèle BART local n'a pas été trouvé : {model_name_or_path}\n\nTéléchargez le modèle 'facebook/bart-base' sur une machine avec Internet, puis copiez tous les fichiers dans ce dossier.")
        self.tokenizer = BartTokenizer.from_pretrained(model_name_or_path)
        self.model = BartForConditionalGeneration.from_pretrained(model_name_or_path).to(self.device)
        self.trained = False

    def train(self, X, y, sample_weight=None, epochs=3, batch_size=4):
        from torch.utils.data import DataLoader, Dataset
        from transformers import AdamW
        class SimpleDataset(Dataset):
            def __init__(self, X, y, tokenizer, max_length=128):
                self.X = X
                self.y = y
                self.tokenizer = tokenizer
                self.max_length = max_length
            def __len__(self):
                return len(self.X)
            def __getitem__(self, idx):
                source = self.tokenizer(self.X[idx], truncation=True, padding='max_length', max_length=self.max_length, return_tensors="pt")
                target = self.tokenizer(self.y[idx], truncation=True, padding='max_length', max_length=self.max_length, return_tensors="pt")
                return {
                    'input_ids': source['input_ids'].squeeze(),
                    'attention_mask': source['attention_mask'].squeeze(),
                    'labels': target['input_ids'].squeeze()
                }
        dataset = SimpleDataset(X, y, self.tokenizer)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        optimizer = AdamW(self.model.parameters(), lr=5e-5)
        self.model.train()
        for epoch in range(epochs):
            for batch in loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()
        self.trained = True
        return float(loss.detach().cpu())

    def predict(self, x, max_length=64):
        self.model.eval()
        input_ids = self.tokenizer(x, return_tensors="pt").input_ids.to(self.device)
        with torch.no_grad():
            output_ids = self.model.generate(input_ids, max_length=max_length)
        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

    def save(self, path):
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)

    @classmethod
    def load(cls, path):
        obj = cls(model_name_or_path=path)
        return obj

# Fonctions de haut niveau pour compatibilité pipeline
model_instance = None

def train(X, y, sample_weight=None, epochs=3, batch_size=4):
    global model_instance
    model_instance = Seq2SeqModel()
    return model_instance.train(X, y, sample_weight, epochs, batch_size)

def predict(x):
    global model_instance
    if model_instance is None:
        model_instance = Seq2SeqModel()
    return model_instance.predict(x)

def save(path):
    global model_instance
    if model_instance:
        model_instance.save(path)

