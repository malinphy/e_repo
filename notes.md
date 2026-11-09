# ☸️ Kubernetes & `kubectl` Referans Notları (`notes.md`)

Bu doküman, projedeki Kubernetes YAML dosyalarının ([`k8s/`](./k8s) ve [`k8s-single/kubernetes.yaml`](./k8s-single/kubernetes.yaml)) ne işe yaradığını, birbirleriyle nasıl bağlantılı olduğunu ve sık kullanılan tüm **`kubectl`** komutlarını içerir.

---

## 🚀 Hızlı Başlangıç: Docker Desktop'ta Adım Adım Çalıştırma Komutları

Projeyi sıfırdan Kubernetes üzerinde ayağa kaldırmak, loglarını izlemek ve durdurmak için sırasıyla çalıştırılması gereken komutlar:

### Adım 1: Docker İmajını Oluşturma (İlk kurulumda veya kod değiştiğinde)
```powershell
docker build -t shopagent/shopagent:latest .
```

### Adım 2: Namespace Oluşturma
```powershell
kubectl apply -f k8s/namespace.yaml
```

### Adım 3: `.env` Dosyasından Secret Oluşturma (Boşluk ve Tırnakları Temizleyerek)
> **Önemli:** `.env` içindeki `=` etrafındaki boşlukları ve `"` çift tırnakları temizleyip Kubernetes Secret olarak yükler:
```powershell
(Get-Content .env) -replace '\s*=\s*', '=' -replace '["'']', '' | Set-Content .env.k8s
kubectl create secret generic shopagent-secrets --from-env-file=.env.k8s -n shopagent --dry-run=client -o yaml | kubectl apply -f -
Remove-Item .env.k8s
```

### Adım 4: ConfigMap, Kalıcı Disk (PVC), Deployment ve Service'i Başlatma
```powershell
kubectl apply -f k8s/configmap.yaml -f k8s/pvc.yaml -f k8s/deployment.yaml -f k8s/service.yaml
```

### Adım 5: Pod'un Ayağa Kalktığını Kontrol Etme
```powershell
kubectl rollout status deployment/shopagent -n shopagent
kubectl get all,pvc -n shopagent
```

### Adım 6: Tarayıcıdan Erişmek İçin Port Yönlendirme (`http://localhost:8000`)
```powershell
kubectl port-forward svc/shopagent-service 8000:80 -n shopagent
```
* **Web Arayüzü:** http://localhost:8000
* **Swagger API:** http://localhost:8000/docs

### Adım 7: Backend Loglarını Canlı İzleme (Ayrı bir terminalde)
```powershell
kubectl logs -f deployment/shopagent -n shopagent
```

### Adım 8: Sistemi Tamamen Durdurma ve Kaldırma
```powershell
kubectl delete namespace shopagent
```

---

## 1. `docker-compose.yml` ile Kubernetes Dosyalarının Karşılaştırması

Docker Compose'da tek dosyada yazdığımız her ayar, Kubernetes'te ayrı bir nesneye (`kind`) karşılık gelir:

| `docker-compose.yml` Karşılığı | Kubernetes Nesnesi (`kind`) | Dosya (`k8s/`) | Ne İşe Yarar? |
| :--- | :--- | :--- | :--- |
| *(Proje klasörü / izolasyon)* | `Namespace` | [`k8s/namespace.yaml`](./k8s/namespace.yaml) | Tüm kaynakları `shopagent` adlı izole alanda toplar. |
| `env_file: .env` *(genel ayarlar)* | `ConfigMap` | [`k8s/configmap.yaml`](./k8s/configmap.yaml) | Gizli olmayan ayarları (`PORT=8000`, `SQLITE_DB_PATH` vb.) tutar. |
| `env_file: .env` *(API şifreleri)* | `Secret` | [`k8s/secret.yaml`](./k8s/secret.yaml) | `OPENAI_API_KEY` ve `SERPAPI_API_KEY` gibi gizli anahtarları tutar. |
| `volumes: ./data:/app/backend/data` | `PersistentVolumeClaim` | [`k8s/pvc.yaml`](./k8s/pvc.yaml) | SQLite (`ecommerce.db`, `checkpoints.db`) silinmesin diye `2Gi` kalıcı disk bağlar. |
| `image:` + `restart: unless-stopped` | `Deployment` | [`k8s/deployment.yaml`](./k8s/deployment.yaml) | Konteyneri çalıştırır, `/health` kontrolü yapar, çökerse yeniden başlatır. |
| `ports: "8000:8000"` | `Service` | [`k8s/service.yaml`](./k8s/service.yaml) | Pod'a sabit bir iç IP/DNS (`shopagent-service`) verir ve trafiği `8000` portuna iletir. |
| *(Reverse Proxy / Domain)* | `Ingress` | [`k8s/ingress.yaml`](./k8s/ingress.yaml) | `http://shopagent.local` alan adını servise yönlendirir. |
| *(Hepsini tek komutta kurma)* | `Kustomization` | [`k8s/kustomization.yaml`](./k8s/kustomization.yaml) | Tüm dosyaları doğru sırayla (`kubectl apply -k k8s/`) uygular. |

> **Not:** Tüm bu dosyaların tek bir dosyada birleştirilmiş hali [`k8s-single/kubernetes.yaml`](./k8s-single/kubernetes.yaml) içindedir.

---

## 2. Dosyalar Birbirine Nasıl Bağlanıyor?

Merkezde **[`k8s/deployment.yaml`](./k8s/deployment.yaml)** vardır; diğer tüm dosyalar isimleriyle (`metadata.name`) ona takılır:

```text
configmap.yaml (shopagent-config)  ──┐
secret.yaml    (shopagent-secrets) ──┼──► deployment.yaml (Pod: Port 8000)
pvc.yaml       (shopagent-data-pvc)──┘           ▲
                                                 │ (selector: app.kubernetes.io/name: shopagent)
                                          service.yaml (shopagent-service: Port 80 -> 8000)
                                                 ▲
                                                 │
                                          ingress.yaml (http://shopagent.local)
```

---

## 3. Açıklayıcı Sözlük Komutları (`kubectl explain`)

YAML içindeki bir alanın ne işe yaradığını internete bakmadan doğrudan terminalden öğrenmek için kullanılır:

```bash
# Sistemdeki tüm Kubernetes kaynak türlerini (shortnames dahil) listeler
kubectl api-resources

# Deployment nesnesinin ne olduğunu ve ana alanlarını açıklar
kubectl explain deployment

# Deployment altındaki spec ayarlarını (replicas, strategy vb.) açıklar
kubectl explain deployment.spec

# Strategy (RollingUpdate vs Recreate) alanını açıklar
kubectl explain deployment.spec.strategy

# Container içindeki livenessProbe / readinessProbe parametrelerini açıklar
kubectl explain deployment.spec.template.spec.containers.livenessProbe

# Bir kaynağın altındaki TÜM alanları ağaç yapısında listeler
kubectl explain deployment.spec.template.spec.containers --recursive

# PVC (Kalıcı Disk) ayarlarını açıklar
kubectl explain pvc.spec
```

---

## 4. YAML Yazmadan `kubectl` ile Otomatik YAML Üretme (Yöntem 1 & Yöntem 2)

Sıfırdan boş sayfada YAML yazmak yerine, `kubectl`'in yerleşik komutlarıyla YAML iskeletini otomatik oluşturabilirsiniz.

### Yöntem 1: Önce Cluster'da Çalıştırıp, Sonra YAML'ını Çıkarmak
Hiç YAML dosyası yazmadan doğrudan komutla (`imperative`) kaynağı ayağa kaldırıp, ardından çalışan kaynağın YAML çıktısını dosyaya aktarabilirsiniz:

```bash
# 1. Hiç YAML yazmadan doğrudan Deployment oluştur ve cluster'da çalıştır
kubectl create deployment shopagent --image=shopagent/shopagent:latest --port=8000

# 2. Çalışan bu Deployment'ın YAML halini dosyaya aktar
kubectl get deployment shopagent -o yaml > deployment.yaml

# 3. Aynı şekilde hiç YAML yazmadan Service olarak dışarı aç (port 80 -> 8000)
kubectl expose deployment shopagent --name=shopagent-service --port=80 --target-port=8000

# 4. Oluşan Service'in de YAML halini dosyaya kaydet
kubectl get service shopagent-service -o yaml > service.yaml
```
> **Not:** Çalışan bir kaynaktan `kubectl get ... -o yaml` aldığınızda, Kubernetes içine çalışma zamanı durum bilgilerini (`status:`, `uid`, `resourceVersion`, `creationTimestamp`) de ekler.

---

### Yöntem 2: Cluster'a Hiç Kurmadan Temiz Şablon Üretmek (`--dry-run=client -o yaml`) ⭐ *(En Çok Tercih Edilen)*
Komutun sonuna `--dry-run=client -o yaml` eklendiğinde Kubernetes bunu cluster'a kurmaz; "kurulsaydı YAML dosyası nasıl olurdu?" diyerek **tertemiz, gereksiz sistem satırları olmayan** bir YAML çıktısı üretir:

```bash
# 1. Deployment YAML şablonunu tek satırla otomatik üret:
kubectl create deployment shopagent \
  --image=shopagent/shopagent:latest \
  --port=8000 \
  --replicas=1 \
  -n shopagent \
  --dry-run=client -o yaml > deployment.yaml

# 2. Service YAML şablonunu otomatik üret:
kubectl create service clusterip shopagent-service \
  --tcp=80:8000 \
  -n shopagent \
  --dry-run=client -o yaml > service.yaml

# 3. ConfigMap YAML şablonunu otomatik üret:
kubectl create configmap shopagent-config \
  --from-literal=HOST=0.0.0.0 \
  --from-literal=PORT=8000 \
  -n shopagent \
  --dry-run=client -o yaml > configmap.yaml

# 4. Secret YAML şablonunu mevcut .env dosyasından otomatik üret:
kubectl create secret generic shopagent-secrets \
  --from-env-file=.env \
  -n shopagent \
  --dry-run=client -o yaml > secret.yaml

# 5. Ingress YAML şablonunu otomatik üret:
kubectl create ingress shopagent-ingress \
  --class=nginx \
  --rule="shopagent.local/*=shopagent-service:80" \
  -n shopagent \
  --dry-run=client -o yaml > ingress.yaml

# 6. Namespace YAML şablonunu otomatik üret:
kubectl create namespace shopagent --dry-run=client -o yaml > namespace.yaml
```

---

## 5. Kurulum ve Uygulama Komutları (`apply` & `create`)

```bash
# YÖNTEM A: Tek dosya üzerinden tüm sistemi kurma
kubectl apply -f k8s-single/kubernetes.yaml

# YÖNTEM B: Çoklu klasör üzerinden Kustomize ile doğru sırada kurma
kubectl apply -k k8s/

# YÖNTEM C: Sadece tek bir dosyayı (örneğin sadece Deployment'ı) güncelleme
kubectl apply -f k8s/deployment.yaml

# DRY-RUN: Cluster'a hiçbir şey kurmadan YAML dosyalarında yazım/şema hatası var mı test etme
kubectl apply -f k8s-single/kubernetes.yaml --dry-run=client
```

### `.env` Dosyasından Doğrudan Secret Oluşturma
[`k8s/secret.yaml`](./k8s/secret.yaml) içine gerçek API anahtarlarınızı elle yazmak istemiyorsanız, mevcut `.env` dosyanızı doğrudan Kubernetes Secret olarak yükleyebilirsiniz:

```bash
# Namespace yoksa önce oluştur
kubectl apply -f k8s/namespace.yaml

# .env dosyasındaki değişkenleri shopagent-secrets olarak cluster'a yükle/güncelle
kubectl create secret generic shopagent-secrets \
  --from-env-file=.env \
  -n shopagent \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 6. Durum Kontrolü ve İnceleme Komutları (`get` & `describe`)

```bash
# shopagent namespace'indeki tüm çalışan kaynakları (Pod, Service, Deployment, ReplicaSet) gör
kubectl get all -n shopagent

# Pod'ları hangi node üzerinde çalıştığı ve IP bilgileriyle detaylı listele
kubectl get pods -n shopagent -o wide

# Pod durumlarını canlı (anlık değişimlerle) izle (Çıkmak için Ctrl+C)
kubectl get pods -n shopagent -w

# Kalıcı diskin (PVC) bağlanıp bağlanmadığını (Bound durumu) kontrol et
kubectl get pvc -n shopagent

# ConfigMap ve Secret listesini gör
kubectl get configmap,secret -n shopagent

# Ingress (Domain yönlendirme) durumunu gör
kubectl get ingress -n shopagent
```

### Hata Ayıklama İçin Detaylı İnceleme (`describe` & `events`)
Bir pod `Pending`, `CrashLoopBackOff` veya `ImagePullBackOff` durumunda takılı kalırsa sebebini görmek için:

```bash
# Deployment ve Pod'un tüm detaylarını ve son olaylarını (Events) gösterir
kubectl describe deployment shopagent -n shopagent
kubectl describe pod -l app.kubernetes.io/name=shopagent -n shopagent

# PVC neden bağlanmadıysa (Pending) sebebini gösterir
kubectl describe pvc shopagent-data-pvc -n shopagent

# Namespace içindeki tüm sistem olaylarını (Events) zaman sırasına göre listeler
kubectl get events -n shopagent --sort-by='.lastTimestamp'

# Pod'un anlık CPU ve RAM tüketimini gösterir (metrics-server kuruluysa)
kubectl top pods -n shopagent
```

---

## 7. Log İzleme ve Konteyner İçine Bağlanma (`logs` & `exec`)

```bash
# Uygulamanın (FastAPI / Uvicorn) loglarını görüntüle
kubectl logs deployment/shopagent -n shopagent

# Logları canlı olarak (tail -f gibi) akan şekilde takip et
kubectl logs -f deployment/shopagent -n shopagent

# Son 100 satır logu göster
kubectl logs --tail=100 deployment/shopagent -n shopagent

# Eğer pod çöktüyse ve yeniden başladıysa, ÇÖKMEDEN ÖNCEKİ konteynerin loglarını göster
kubectl logs deployment/shopagent -n shopagent --previous
```

### Çalışan Konteynerin İçine Terminal Açma (`exec`)
```bash
# Çalışan pod'un içinde interaktif bash terminali aç
kubectl exec -it deployment/shopagent -n shopagent -- /bin/bash

# Konteyner içine girmeden SQLite veritabanı dosyalarının (/app/backend/data) oluştuğunu kontrol et
kubectl exec deployment/shopagent -n shopagent -- ls -lh /app/backend/data

# Konteyner içinden /health endpoint'ini test et
kubectl exec deployment/shopagent -n shopagent -- curl -s http://localhost:8000/health
```

---

## 8. Lokal Bilgisayardan Erişim (`port-forward`)

`Ingress` kurmadan veya domain ayarlamadan, doğrudan kendi bilgisayarınızdaki tarayıcıdan (`http://localhost:8000`) uygulamaya erişmek için:

```bash
# Servisin 80 portunu bilgisayarınızın 8000 portuna bağlar
kubectl port-forward svc/shopagent-service 8000:80 -n shopagent
```
* Tarayıcıda açın: **http://localhost:8000**
* Swagger API Dokümantasyonu: **http://localhost:8000/docs**

---

## 9. Yeniden Başlatma, Güncelleme ve Silme (`rollout` & `delete`)

```bash
# ConfigMap veya Secret değiştirdikten sonra Pod'u yeniden başlatma
kubectl rollout restart deployment/shopagent -n shopagent

# Dağıtımın (rollout) tamamlanma durumunu izleme
kubectl rollout status deployment/shopagent -n shopagent

# Yeni versiyonda sorun çıkarsa bir önceki çalışan versiyona geri dönme (Rollback)
kubectl rollout undo deployment/shopagent -n shopagent

# Sadece pod'u silip Deployment'ın onu temiz şekilde yeniden oluşturmasını sağlama
kubectl delete pod -l app.kubernetes.io/name=shopagent -n shopagent
```

### Tüm Kaynakları Kaldırma (Temizlik)
```bash
# Tek dosya ile kurduysanız tüm kaynakları siler:
kubectl delete -f k8s-single/kubernetes.yaml

# Çoklu klasör (Kustomize) ile kurduysanız tüm kaynakları siler:
kubectl delete -k k8s/

# Veya doğrudan shopagent namespace'ini silerek içindeki her şeyi (PVC dahil) temizler:
kubectl delete namespace shopagent
```

---

## 10. Resmi Kubernetes Dokümantasyon Referansları

* **Kubernetes Kavramlar Rehberi:** https://kubernetes.io/docs/concepts/
* **`kubectl` Cheat Sheet (Resmi Hızlı Referans):** https://kubernetes.io/docs/reference/kubectl/cheatsheet/
* **Deployment:** https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
* **Service:** https://kubernetes.io/docs/concepts/services-networking/service/
* **ConfigMap:** https://kubernetes.io/docs/concepts/configuration/configmap/
* **Secret:** https://kubernetes.io/docs/concepts/configuration/secret/
* **PersistentVolumeClaim (PVC):** https://kubernetes.io/docs/concepts/storage/persistent-volumes/
* **Ingress:** https://kubernetes.io/docs/concepts/services-networking/ingress/
* **Kustomize:** https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/
