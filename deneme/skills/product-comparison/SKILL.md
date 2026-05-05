---
name: product-comparison
description: Use this skill when the user wants to compare prices or search for products on Amazon, eBay, and Walmart.
---

# Product Comparison Skill

## Overview
This skill allows the agent to search for product information across Amazon, eBay, and Walmart using SerpApi.

## Instructions

### 1. Ürünü Belirle
- Ürün adını ayıkla.
- **ÖNEMLİ**: Kullanıcı "snickers" yazarsa, %99 ihtimalle "sneakers" (ayakkabı) demek istiyordur. Aramayı "sneakers" olarak düzelt.

### 2. Aramayı Yap
- `compare_prices` aracını kullan.

### 3. Çıktı Formatı (KESİNLİKLE UYULMALI)
Yanıtını **MUTLAKA** şu yapıda oluştur:
1. **Karşılaştırma Tablosu**: Ürün, Fiyat, Kaynak (Amazon/eBay/Walmart) ve Link sütunlarından oluşan bir Markdown tablosu oluştur.
2. **En İyi Fırsat**: Hangi ürünün en avantajlı olduğunu belirt.
3. **Tamamlayıcı Öneriler**: Kullanıcının aradığı ürünle birlikte işine yarayacak 2-3 tamamlayıcı ürün önerisi yap (Örn: ayakkabı için çorap veya temizleme kiti). Neden önerdiğini açıkla. (Bu adım için `product-recommendation` becerindeki mantığı kullan).

### 4. Dil
- **HER ZAMAN** kullanıcının dilinde yanıt ver (Türkçe sorulduysa Türkçe yanıtla).

